class Optimizer:
    """
    This class represents the base class optimization implementations for different resource
    management techniques.
    Each implementation must implement the run method.
    The run method starts the optimization indefinitely.
    A commonly used method is to implement a reconciliation loop that repeatedly makes decision.
    But it is also possible to implement other strategies (i.e., event-based).
    The only constraint is, that executing the `run` method will start this process.
    Initialization can take place in the implementation's constructor or in the setup method that must be called
    before executing the run method.
    The stop method should abort the process and cleanup any open resources.
    """

    def setup(self): ...

    def run(self): ...

    def stop(self): ...