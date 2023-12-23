from faas.opt.api import Optimizer


class ReconciliationOptimizationDaemon(Optimizer):

    def __init__(self, optimizer: Optimizer, use_yield: bool = False):
        self.is_running = True
        self.optimizer = optimizer
        self.use_yield = use_yield

    def sleep(self): ...

    def setup(self):
        self.optimizer.setup()

    def run(self):
        if self.use_yield:
            yield from self.optimizer.run()
        else:
            self.optimizer.run()

        while self.is_running:
            if self.use_yield:
                yield from self.sleep()
                yield from self.optimizer.run()
            else:
                self.sleep()
                self.optimizer.run()

    def stop(self):
        self.optimizer.stop()
        self.is_running = False
