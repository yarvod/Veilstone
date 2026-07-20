from __future__ import annotations

import tomllib

from voxel_sandbox import __version__
from voxel_sandbox.__main__ import build_parser


def test_cli_defaults_to_client() -> None:
    parser = build_parser()
    assert parser.parse_args([]).command is None


def test_package_exposes_version() -> None:
    with open("pyproject.toml", "rb") as pyproject:
        metadata = tomllib.load(pyproject)
    assert __version__ == metadata["project"]["version"]


def test_developer_benchmark_commands_are_registered() -> None:
    parser = build_parser()
    for command in (
        "benchmark-mesher",
        "benchmark-worldgen",
        "benchmark-physics",
        "benchmark-lighting",
        "benchmark-streaming",
        "benchmark-frame-streaming",
        "benchmark-network",
        "benchmark-server",
        "benchmark-shadows",
    ):
        assert parser.parse_args([command]).command == command


def test_frame_streaming_benchmark_accepts_low_end_contract_options() -> None:
    args = build_parser().parse_args(
        [
            "benchmark-frame-streaming",
            "--quality-preset",
            "low_60",
            "--width",
            "1280",
            "--height",
            "720",
            "--generation-workers",
            "1",
            "--meshing-workers",
            "1",
            "--path",
            "walk",
            "--movement-speed",
            "5",
            "--startup-timeout",
            "15",
            "--startup-mode",
            "full",
            "--backend",
            "standalone",
            "--screenshot-output",
            "saves/benchmarks/rd12.png",
        ]
    )

    assert args.quality_preset == "low_60"
    assert (args.width, args.height) == (1280, 720)
    assert (args.generation_workers, args.meshing_workers) == (1, 1)
    assert args.path == "walk"
    assert args.movement_speed == 5.0
    assert args.startup_timeout == 15.0
    assert args.startup_mode == "full"
    assert args.backend == "standalone"
    assert args.screenshot_output == "saves/benchmarks/rd12.png"


def test_client_accepts_connect_address_and_nickname() -> None:
    args = build_parser().parse_args(
        ["client", "--connect", "127.0.0.1:25565", "--name", "Veilwalker"]
    )
    assert args.connect == "127.0.0.1:25565"
    assert args.name == "Veilwalker"


def test_server_world_defaults_to_application_data_root() -> None:
    args = build_parser().parse_args(["server"])
    assert args.world is None


def test_structure_preview_accepts_template_key() -> None:
    args = build_parser().parse_args(["structure-preview", "veilstone_ruin"])
    assert args.command == "structure-preview"
    assert args.template == "veilstone_ruin"


def test_gameplay_smoke_screenshot_command_accepts_runtime_options() -> None:
    args = build_parser().parse_args(
        [
            "gameplay-smoke-screenshot",
            "--frames",
            "12",
            "--render-distance",
            "4",
            "--metadata",
            "saves/screenshots/smoke.json",
        ]
    )
    assert args.command == "gameplay-smoke-screenshot"
    assert args.frames == 12
    assert args.render_distance == 4
    assert args.metadata == "saves/screenshots/smoke.json"


def test_reference_gameplay_screenshot_command_accepts_runtime_options() -> None:
    args = build_parser().parse_args(
        [
            "reference-gameplay-screenshot",
            "--seed",
            "42",
            "--resource-pack",
            "faithful",
            "--render-distance",
            "3",
            "--output-dir",
            "saves/reference-scene",
        ]
    )
    assert args.command == "reference-gameplay-screenshot"
    assert args.seed == 42
    assert args.resource_pack == "faithful"
    assert args.render_distance == 3
    assert args.output_dir == "saves/reference-scene"


def test_water_surface_smoke_command_accepts_runtime_options() -> None:
    args = build_parser().parse_args(
        [
            "water-surface-smoke",
            "--frames",
            "24",
            "--render-distance",
            "3",
            "--output-dir",
            "saves/water-smoke",
        ]
    )
    assert args.command == "water-surface-smoke"
    assert args.frames == 24
    assert args.render_distance == 3
    assert args.output_dir == "saves/water-smoke"


def test_inventory_interaction_smoke_command_accepts_scenario_and_output() -> None:
    args = build_parser().parse_args(
        [
            "inventory-interaction-smoke",
            "--scenario",
            "left-drag",
            "--output-dir",
            "saves/inventory-smoke",
        ]
    )
    assert args.command == "inventory-interaction-smoke"
    assert args.scenario == "left-drag"
    assert args.output_dir == "saves/inventory-smoke"


def test_input_lifecycle_smoke_command_accepts_output() -> None:
    args = build_parser().parse_args(
        ["input-lifecycle-smoke", "--output-dir", "saves/input-lifecycle"]
    )
    assert args.command == "input-lifecycle-smoke"
    assert args.output_dir == "saves/input-lifecycle"


def test_first_click_smoke_command_accepts_runtime_options() -> None:
    args = build_parser().parse_args(
        [
            "first-click-smoke",
            "--initial-motion",
            "--output-dir",
            "saves/first-click",
        ]
    )
    assert args.command == "first-click-smoke"
    assert args.initial_motion is True
    assert args.output_dir == "saves/first-click"


def test_swim_audio_smoke_command_accepts_output() -> None:
    args = build_parser().parse_args(["swim-audio-smoke", "--output-dir", "saves/swim-audio"])
    assert args.command == "swim-audio-smoke"
    assert args.output_dir == "saves/swim-audio"


def test_update_commands_are_registered() -> None:
    parser = build_parser()
    assert parser.parse_args(["check-update"]).command == "check-update"
    args = parser.parse_args(["download-update", "--output-dir", "saves/updates"])
    assert args.command == "download-update"
    assert args.output_dir == "saves/updates"
