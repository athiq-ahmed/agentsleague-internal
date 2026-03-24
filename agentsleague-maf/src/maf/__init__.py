"""maf — Microsoft Agent Framework orchestration layer for CertPrep."""
import sys, pathlib

# Allow importing models/guardrails from the existing agentsleague-foundry-sdk source
_SDK_SRC = pathlib.Path(__file__).parents[3] / "agentsleague-foundry-sdk" / "src"
if str(_SDK_SRC) not in sys.path:
    sys.path.insert(0, str(_SDK_SRC))
