from django.test import SimpleTestCase

from .marl.env import SaRaDECoordinationEnv
from .marl.orchestrator import state_from_context


class SaRaDEMARLTests(SimpleTestCase):
    def test_environment_shapes_and_step(self):
        env = SaRaDECoordinationEnv(seed=1)
        state = env.reset()
        self.assertEqual(state.shape[0], 10)
        obs = env.local_observations(state)
        self.assertEqual(obs.shape[0], 4)
        result = env.step([1, 1, 0, 0])
        self.assertEqual(result.state.shape[0], 10)

    def test_state_encoder_is_bounded(self):
        state = state_from_context({"skills": ["Python"], "research_interests": ["AI"]}, [])
        self.assertEqual(state.shape[0], 10)
        self.assertTrue(((state >= 0) & (state <= 1)).all())
