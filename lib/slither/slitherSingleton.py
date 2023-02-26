from slither.slither import Slither

class SlitherSingleton:
    instance = None

    def __init__(self) -> None:
        self.slither = None

    @staticmethod
    def get_slither_instance():
        if not SlitherSingleton.instance:
            SlitherSingleton.instance = SlitherSingleton()
        return SlitherSingleton.instance
    
    def init_slither_instance(self, target: str, override: bool = False):

        if not target:
            print("this should an exception")

        if not self.slither or (self.slither and override):
            self.slither = Slither(target)




