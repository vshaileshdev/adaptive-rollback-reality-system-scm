from .config import settings

class CheckpointController:
    def __init__(self):
        self.state_counter = 0
        self.total_states_received = 0
        self.total_checkpoints_saved = 0

    def evaluate(self, status: str) -> tuple[int, bool]:
        """
        Returns (checkpoint_frequency, should_save)
        """
        self.total_states_received += 1

        if status == "CRITICAL":
            freq = settings.CRITICAL_CHECKPOINT_FREQ
        elif status == "WARNING":
            freq = settings.WARNING_CHECKPOINT_FREQ
        else:
            freq = settings.NORMAL_CHECKPOINT_FREQ

        self.state_counter += 1
        should_save = False

        if self.state_counter >= freq:
            should_save = True
            self.state_counter = 0
            self.total_checkpoints_saved += 1

        return freq, should_save

    def get_metrics(self):
        return {
            "total_states_received": self.total_states_received,
            "total_checkpoints": self.total_checkpoints_saved,
            "storage_saved": self.total_states_received - self.total_checkpoints_saved
        }

    def reset(self):
        """Cleanly resets runtime counters and metrics."""
        self.state_counter = 0
        self.total_states_received = 0
        self.total_checkpoints_saved = 0

checkpoint_controller = CheckpointController()
