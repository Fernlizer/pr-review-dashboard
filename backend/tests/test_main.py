import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import main


class LifespanTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_schedules_initial_poll_without_awaiting_it(self):
        app = SimpleNamespace(state=SimpleNamespace())
        scheduler = MagicMock()

        with patch.object(main, "scheduler", scheduler), patch.object(
            main, "init_db", new=AsyncMock()
        ), patch.object(main, "scheduled_poll", new=AsyncMock()) as initial_poll:
            async with main.lifespan(app):
                initial_poll.assert_not_awaited()
                scheduler.start.assert_called_once_with()
                self.assertTrue(app.state.poller_enabled)

        jobs = scheduler.add_job.call_args_list
        initial_jobs = [
            call
            for call in jobs
            if call.kwargs.get("id") == "initial_pr_poll"
        ]
        self.assertEqual(len(initial_jobs), 1)
        self.assertIs(initial_jobs[0].args[0], initial_poll)
        self.assertEqual(initial_jobs[0].args[1], "date")
        scheduler.shutdown.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
