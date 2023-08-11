from functools import wraps
import inspect
from typing import Any, Dict, Type

import pydantic


class ValidationModel(pydantic.BaseModel):

    def populate_obj(self, obj, **kwargs):
        if 'exclude_unset' not in kwargs:
            kwargs['exclude_unset'] = True

        for key, value in self.dict(**kwargs).items():
            setattr(obj, key, value)

    def create_obj(self, cls, **kwargs):
        if 'exclude_unset' not in kwargs:
            kwargs['exclude_unset'] = True

        return cls(**self.dict(**kwargs))


# def _validate_signature_length(parameters):
#     # TODO: Needed another, more stable way for detecting methods and functions
#     #  inspect.ismethod works only on instances, not on class functions
#     needed_len = 2 if 'self' in parameters else 1
#     return len(parameters) == needed_len
#
#
# def _get_last_param(parameters):
#     # We need to take last key in dict,
#     # but can't do dict.keys()[-1]
#     name = next(reversed(parameters.keys()))
#     return parameters[name]
#
#
# def validate_with_model(fn):
#     """
#     Decorator for function and methods,
#     receiving one parameter - validation model.
#     """
#     signature = inspect.signature(fn)
#
#     assert _validate_signature_length(signature.parameters), \
#         f'Callable, decorated by validate_with_dto, ' \
#         f'must have only 1 parameter!'
#
#     dto_param = _get_last_param(signature.parameters)
#     assert issubclass(dto_param.annotation, ValidationModel), \
#         f'Argument of {fn} must be a ValidationModel! ' \
#         f'Argument {dto_param.name} is {dto_param.annotation}'
#
#     dto_cls = dto_param.annotation
#
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         # TODO: args passed to target function for working with methods.
#         #  If wrapped function will be called with any args, args will be passed
#         #  to target function. Validation of args number in decorator
#         #  prevents it, but this looks ugly
#         return fn(*args, dto_cls(**kwargs))
#
#     setattr(wrapper, '__annotations__', dto_cls.__annotations__)
#
#     return wrapper


def validate_with_models(fn):
    """
    Decorator for function and methods,
    receiving one parameter - validation model.
    """
    signature = inspect.signature(fn)

    validators: Dict[str, Type[ValidationModel]] = {}
    params_without_models: Dict[str, Any] = {}

    for name, param in signature.parameters.items():
        if issubclass(param.annotation, ValidationModel):
            validators[name] = param.annotation
        else:
            params_without_models[name] = param.annotation

    validator_for_args: Type[pydantic.BaseModel] = pydantic.create_model(
        fn.__name__, **params_without_models
    )

    def _validate(**kwargs):
        kwargs_ = {
            name: validator(**kwargs)
            for name, validator in validators.items()
        }
        kwargs_.update(validator_for_args(**kwargs).dict())
        return kwargs_

    @wraps(fn)
    def _wrapper(*args, **kwargs):
        return fn(*args, **_validate(**kwargs))

    _wrapper.validate = _validate
    _wrapper.as_is = fn

    return fn


def _is_method_with_model(fn) -> bool:
    signature = inspect.signature(fn)
    for param in signature.parameters.values():
        if inspect.isclass(param.annotation):
            if issubclass(param.annotation, ValidationModel):
                return True

    return False


def validate(fn):
    if _is_method_with_model(fn):
        return validate_with_models(fn)
    else:
        return pydantic.validate_arguments(fn)
