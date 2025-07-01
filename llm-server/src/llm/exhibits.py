import yaml
from util import get_resource


class ExhibitManager:

    def __init__(self, list_resource: str):
        with open(get_resource(list_resource), 'r') as fd:
            text = fd.read()

        self.exhibits: dict = yaml.load(text, Loader=yaml.Loader)['exhibits']

    def get_exhibit_keys(self):
        """Gets ALL the exhibit keys"""
        return [key for key in self.exhibits]

    def get_active_exhibit_keys(self):
        """Gets only the active exhibit keys"""
        return [key for key in self.exhibits if self.is_active(key)]

    def exists(self, key: str):
        """Checks if an exhibit key exists
        
        Args:
            key (str): The exhibit key to check for
        """
        return key in self.get_exhibit_keys()

    def is_active(self, key: str):
        """Checks if an exhibit key is activated
        
        Args:
            key (str): The exhibit key to check for
        """
        return self.exists(key) and self.exhibits[key]['active']

    def set_active(self, key: str, active: bool):
        """Activates an exhibit key, if possible
        
        Args:
            key (str): The key to change the activity state of
            active (bool): Should the key be activated or deactivated?
        """
        if self.exists(key):
            self.exhibits[key]['active'] = active
        else:
            raise Exception(f'Key {key} does not exist!')
