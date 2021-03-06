import warnings
import json

class FromDictMixin():
    def __init__(self, *args, **kwargs):
        # apply json properties to existing attributes
        attributes = self.__dict__.keys()
        if args:
            if len(args) > 1:
                warnings.warn("Positional arguments after the first are ignored.")
            struct = args[0]
            for key in struct:
                if key in attributes:
                    setattr(self, key, self.load_attribute(key, struct[key]))
                else:
                    warnings.warn("JSON field {} ignored.".format(key))

        # override any json properties with the named ones
        for key in kwargs:
            if key in attributes:
                setattr(self, key, self.load_attribute(key, kwargs[key]))
            else:
                warnings.warn("Keyword argument {} ignored.".format(key))

    def load_attribute(self, key, value):
        return value

    def dump(self):
        prop_dict = vars(self)
        return recursive_dump(prop_dict)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
            all(getattr(other, attr, None) == getattr(self, attr, None) for attr in self.__dict__.keys()))

    def __hash__(self):
        return hash(json.dumps(self.dump()))

def recursive_dump(value):
    # recursively call dump() for nested objects to generate a json-serializable dict
    # this is not entirely reversible because there is no distinction between sets and lists in dict form
    if isinstance(value, dict):
        return {key:recursive_dump(value[key]) for key in value}
    elif isinstance(value, list):
        return [recursive_dump(v) for v in value]
    elif isinstance(value, set):
        return [recursive_dump(v) for v in value]
    else:
        try:
            return value.dump()
        except AttributeError:
            return value
