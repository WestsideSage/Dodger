import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tests.test_regression import _baseline_setup
from dodgeball_sim.engine import MatchEngine
import json

result = MatchEngine().run(_baseline_setup(), seed=31415)
print(json.dumps(result.to_dict(), indent=2))