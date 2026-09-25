"""CLI entry point for computer-use automation system."""

import asyncio
import argparse
import json
import os
from pathlib import Path
from anthropic import Anthropic

from .config import Config
from .models.artifact import CapabilityArtifact
from .agent.discovery import DiscoveryAgent
from .agent.replay import ReplayEngine
from .surfaces.web import WebSurface
from .safety.guardrails import GuardrailEngine
from .safety.redaction import Redactor
from .escalation.detector import StuckDetector
from .escalation.handoff import HandoffManager
from .observability.logger import StructuredLogger
from .observability.evidence import EvidenceCollector


async def run_discovery(args, config: Config):
    """Run LLM-driven discovery."""
    print(f"\n🔍 Starting discovery: {args.goal}")
    print(f"📍 Entry point: {args.entry_point}\n")
    # Initialize components

    client = Anthropic(api_key=config.anthropic_api_key)
    logger = StructuredLogger("discovery", config.safety.pii_patterns)
    evidence = EvidenceCollector(config.evidence_dir)
    guardrails = GuardrailEngine(config.safety)

    # Parse parameters
    parameters = {}
    if args.parameters:
        parameters = json.loads(args.parameters)

    # Run discovery
    async with WebSurface(config.browser, config.headless) as surface:
        agent = DiscoveryAgent(
            client=client,
            surface=surface,
            guardrails=guardrails,
            logger=logger,
            evidence=evidence,
            max_steps=config.safety.max_steps,
        )

        artifact, result = await agent.discover(
            goal=args.goal, entry_point=args.entry_point, parameters=parameters
        )

    # Save artifact
    artifact_path = f"{config.artifacts_dir}/{artifact.artifact_id}.json"
    os.makedirs(config.artifacts_dir, exist_ok=True)

    with open(artifact_path, "w") as f:
        f.write(artifact.to_json())

    # Save execution result
    result_path = f"{config.evidence_dir}/discovery_{artifact.artifact_id}.json"
    with open(result_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\n✅ Discovery complete!")
    print(f"📄 Artifact saved: {artifact_path}")
    print(f"📊 Result: {result.status.value}")
    print(f"📁 Evidence: {result_path}")

    if result.status.value == "success":
        print(f"\n🎯 Outputs: {json.dumps(result.outputs, indent=2)}")
    else:
        print(f"\n❌ Error: {result.error_message}")

    return artifact, result


async def run_replay(args, config: Config):
    """Run deterministic replay."""
    print(f"\n▶️  Starting replay: {args.artifact}")

    # Load artifact
    artifact_path = args.artifact
    if not artifact_path.endswith(".json"):
        artifact_path = f"{config.artifacts_dir}/{artifact_path}.json"

    with open(artifact_path, "r") as f:
        artifact = CapabilityArtifact.from_json(f.read())

    print(f"📋 Capability: {artifact.name}")

    # Parse parameters
    parameters = {}
    if args.parameters:
        parameters = json.loads(args.parameters)

    print(f"📥 Parameters: {json.dumps(parameters, indent=2)}\n")

    # Initialize components
    logger = StructuredLogger("replay", config.safety.pii_patterns)
    evidence = EvidenceCollector(config.evidence_dir)
    guardrails = GuardrailEngine(config.safety)
    stuck_detector = StuckDetector(config.safety.stuck_detection_threshold)

    # Run replay
    async with WebSurface(config.browser, config.headless) as surface:
        handoff_manager = HandoffManager(surface, logger)

        engine = ReplayEngine(
            surface=surface,
            guardrails=guardrails,
            logger=logger,
            evidence=evidence,
            stuck_detector=stuck_detector,
            handoff_manager=handoff_manager,
        )

        result = await engine.replay(artifact, parameters)

    # Save result
    result_path = f"{config.evidence_dir}/replay_{artifact.artifact_id}_{result.execution_id}.json"
    with open(result_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\n✅ Replay complete!")
    print(f"📊 Status: {result.status.value}")
    print(f"📁 Evidence: {result_path}")

    if result.status.value == "success":
        print(f"\n🎯 Outputs: {json.dumps(result.outputs, indent=2)}")
    elif result.status.value == "business_outcome":
        print(f"\n📌 Business Outcome: {result.business_outcome}")
    elif result.status.value == "escalated":
        print(f"\n🚨 Escalated: {result.escalation_reason}")
    else:
        print(f"\n❌ Error: {result.error_message}")
        if result.failed_step_id:
            print(f"   Failed at step: {result.failed_step_id}")

    return result


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Computer-Use Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
    # Discovery: Learn a new capability
    python -m src.main discover \\
        --goal "Look up member 12345 and read their savings balance" \\
        --entry-point "http://localhost:5000/search" \\
        --parameters '{"member_id": "12345"}'
    
    # Replay: Execute saved capability
    python -m src.main replay \\
        --artifact cap_search_5 \\
        --parameters '{"member_id": "67890"}'
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Discovery command
    discover_parser = subparsers.add_parser("discover", help="Run LLM-driven discovery")
    discover_parser.add_argument("--goal", required=True, help="Goal to accomplish")
    discover_parser.add_argument(
        "--entry-point", required=True, help="Starting URL or app"
    )
    discover_parser.add_argument("--parameters", help="JSON parameters")
    discover_parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode"
    )

    # Replay command
    replay_parser = subparsers.add_parser("replay", help="Replay saved artifact")
    replay_parser.add_argument("--artifact", required=True, help="Artifact ID or path")
    replay_parser.add_argument("--parameters", help="JSON parameters")
    replay_parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load config
    config = Config()
    config.validate()

    if hasattr(args, "headless") and args.headless:
        config.headless = True

    # Run command
    if args.command == "discover":
        asyncio.run(run_discovery(args, config))
    elif args.command == "replay":
        asyncio.run(run_replay(args, config))


if __name__ == "__main__":
    main()
