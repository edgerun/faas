from faas.opt.api import Optimizer


class ReconciliationOptimizationDaemon(Optimizer):

    def __init__(self, optimizer: Optimizer):
        self.is_running = True
        self.optimizer = optimizer

    def sleep(self): ...

    def setup(self):
        self.optimizer.setup()

    def run(self):
        self.optimizer.run()
        while self.is_running:
            self.sleep()
            self.optimizer.run()

    def stop(self):
        self.optimizer.stop()
        self.is_running = False

