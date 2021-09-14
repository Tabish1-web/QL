
import graphene
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django import DjangoObjectType, converter, utils as graphene_utils
from graphene_django.forms.mutation import ErrorType, get_global_registry, DjangoModelDjangoFormMutationOptions, fields_for_form, OrderedDict, yank_fields_from_attrs, InputField, Field, ClientIDMutation
from graphene.relay.node import from_global_id as from_graphql_global_id
import datetime
from django.forms.models import model_to_dict
import django.db
from graphene.relay.node import to_global_id
from django.db.models.base import Model
from django.core.exceptions import ValidationError


# from helpers.graphql import common
# from api.codes import STATUS_CODE


def get_form_errors(*args):
    arr = []
    for form in args:
        for  field, errors  in form.errors.items():
            arr.append( str(field) + ":" + errors.as_text())
    return arr

def copy_form_errors(form, target_form, exclude=[]):
    for field, messages in form.errors.items():
        if not field in exclude:
            for message in messages:
                target_form.add_error(field, message)

def copy_form_errors_to_field(form, target_form, target_field):
    for field, messages in form.errors.items():
        for message in messages:
            target_form.add_error(target_field, "{field}: {message}".format(field=field, message=message))

def get_form_error_fields(form):
    fields = []
    for field, _messages in form.errors.items():
        fields.append(field)
    return fields

def set_type_from_json(ClassType, json, fields):
    cls_instance = ClassType()
    for field in fields:
        setattr(cls_instance, field, json.get(field))
    return cls_instance

def populate_input_with_data(instance, obj, keys):
    for key in keys:
        value = obj.get(key)
        if not value:
            obj[key] = getattr(instance, key)
    
    return obj

def get_value_at_list_index_safely(list, index):
    try:
        return list[index]
    except:
        return None

def from_global_id(field_name, obj):
    try:
        if isinstance(obj, object):
            if hasattr(obj, field_name):
                value = getattr(obj, field_name)
                if isinstance(value, list):
                    value = from_global_id_array(field_name, value)
                elif value:
                    value = int(from_graphql_global_id(value)[1])
                setattr(obj, field_name, value)
        if isinstance(obj, dict):
            if field_name in obj:
                value = obj.get(field_name, None)
                if isinstance(value, list):
                    value = from_global_id_array(field_name, value)
                elif value:
                    value = int(from_graphql_global_id(value)[1])
                obj[field_name] = value
        return
    except Exception as _e:
        print(_e)
        raise Exception("Invalid id for " + field_name + ".")
    
    raise Exception("Invalid object provided. Object does not have property " + field_name + " in it.")

def from_global_id_multiple(field_names, obj):
    for field in field_names:
        from_global_id(field, obj)

def from_global_id_array(field_name, array):
    if not array:
        return []
    ids = []
    for id in array:
        try:
            ids.append(int(from_graphql_global_id(id)[1]))
        except Exception as _e:
            raise Exception("Couldn't decode one or more base64 ID in " + field_name)
    return ids

def is_datetime_before_today(datetime_instance):
    date = datetime.date(datetime_instance.year, datetime_instance.month, datetime_instance.day)
    return date < datetime.date.today()


class InputObjectTypeModelOptions:
    name = None  # type: str
    description = None  # type: str
    fields = None

    _frozen = False  # type: bool

    def __init__(self, class_type):
        self.class_type = class_type

    def freeze(self):
        self._frozen = True

    def __setattr__(self, name, value):
        if not self._frozen:
            super(InputObjectTypeModelOptions, self).__setattr__(name, value)
        else:
            raise Exception("Can't modify frozen Options {}".format(self))

    def __repr__(self):
        return "<{} name={}>".format(self.__class__.__name__, repr(self.name))

class InputObjectTypeModel(graphene.InputObjectType):

    @classmethod
    def __init_subclass_with_meta__(cls, container=None, _meta=None, form_class=None, only_fields= [], exclude_fields= [], description= None, **options):
        if not form_class:
            raise Exception("form_class is required for utils.InputObjectTypeModel " + cls.__name__) 

        model = form_class._meta.model

        if not model:
            raise Exception("model is required for utils.InputObjectTypeModel " + cls.__name__)

        form = form_class()
        input_fields = fields_for_form(form, only_fields, exclude_fields)
        if "id" not in exclude_fields:
            input_fields["id"] = graphene.ID()

        input_fields = yank_fields_from_attrs(input_fields, _as=InputField)

        _meta = InputObjectTypeModelOptions(cls)
        _meta.fields = input_fields
        _meta.description = description
       
        super(InputObjectTypeModel, cls).__init_subclass_with_meta__(_meta=_meta, container=container, **options)

class BaseDjangoFormMutation(ClientIDMutation):
    class Meta:
        abstract = True

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        form = cls.get_form(root, info, **input)

        if form.is_valid():
            return cls.perform_mutate(form, info)
        else:
            errors = ErrorType.from_errors(form.errors)

            return cls(errors=errors, **form.data)

    @classmethod
    def get_form(cls, root, info, **input):
        form_kwargs = cls.get_form_kwargs(root, info, **input)
        return cls._meta.form_class(**form_kwargs)

    @classmethod
    def get_form_kwargs(cls, root, info, **input):
        kwargs = {"data": input}

        pk = input.get("id", None)
        if pk:
            instance = cls._meta.model._default_manager.get(pk=pk)
            kwargs["instance"] = instance

        return kwargs

class GraphqlModelFormMutation(BaseDjangoFormMutation):
    class Meta:
        abstract = True

    errors = graphene.List(ErrorType)

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        form_class=None,
        model=None,
        return_field_name=None,
        only_fields=(),
        exclude_fields=(),
        return_field_type=None,
        **options
    ):

        if not form_class:
            raise Exception("form_class is required for DjangoModelFormMutation")

        if not model:
            model = form_class._meta.model

        if not model:
            raise Exception("model is required for DjangoModelFormMutation")

        form = form_class()

        if "id" not in exclude_fields:
            update = True
        else:
            update = False
        for i in form.fields:
            if update:
                form.fields[i].required=False

        input_fields = fields_for_form(form, only_fields, exclude_fields)
        if "id" not in exclude_fields:
            input_fields["id"] = graphene.ID()

        registry = get_global_registry()
        model_type = registry.get_type_for_model(model)
        if not model_type:
            raise Exception("No type registered for model: {}".format(model.__name__))

        if not return_field_name:
            model_name = model.__name__
            return_field_name = model_name[:1].lower() + model_name[1:]
        output_fields = OrderedDict()
        output_fields[return_field_name] = graphene.Field(return_field_type or model_type)

        _meta = DjangoModelDjangoFormMutationOptions(cls)
        _meta.form_class = form_class
        _meta.model = model
        _meta.return_field_name = return_field_name
        _meta.fields = yank_fields_from_attrs(output_fields, _as=Field)
        input_fields = yank_fields_from_attrs(input_fields, _as=InputField)
        if input_fields.get("id"):
            input_fields["id"] = graphene.ID(required= True)
        
        input_fields = cls.get_arguments(cls, input_fields)
        super(GraphqlModelFormMutation, cls).__init_subclass_with_meta__(
            _meta=_meta, input_fields=input_fields, **options
        )

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not cls.has_permission(cls, info):
            raise Exception("Permission denied.")
        pk = input.get("id")
        if not pk:
            existing_fields = None

        if pk:
            pk = int(from_graphql_global_id(pk)[1])
            input["id"] = pk
            form_instance_kwargs = cls.get_form_kwargs(root, info, **input)
            existing_fields = model_to_dict(form_instance_kwargs['instance'])
            instance = form_instance_kwargs['instance']

            registry = get_global_registry()

            for i in instance._meta.fields:
                if type(i) is django.db.models.fields.related.ForeignKey:
                    model_type = registry.get_type_for_model(i.remote_field.model)
                    if i.value_from_object(instance):
                        existing_fields[i.name] = to_global_id(str(model_type), i.value_from_object(instance))

        if hasattr(cls, "clean"):
            if existing_fields:
                input = {**existing_fields, **input}
            input = cls.clean(cls, **input)
        else:
            if existing_fields:
                input = {**existing_fields, **input}

        form = cls.get_form(root, info, **input)
        form.context = info.context


        if form.is_valid():

            return cls.perform_mutate(form, info)
        else:
            errors = ErrorType.from_errors(form.errors)

            return cls(errors=errors)

    @classmethod
    def perform_mutate(cls, form, info):
        obj = form.save()
        kwargs = {cls._meta.return_field_name: obj}
        return cls(errors=[], **kwargs)

    def get_arguments(self, input_fields):

        argument_class = getattr(self, "Arguments", None)

        if argument_class:
            
            attribute_names = (i for i in dir(argument_class) if not i.startswith("__"))

            for name in attribute_names:

                input_fields[name] = argument_class.__dict__[name]
        
        return input_fields

    
    def has_permission(cls, info, **kwargs):
        return True


class GraphqlModelFormDeleteMutation(GraphqlModelFormMutation):
    class Meta:
        abstract = True


    @classmethod
    def __init_subclass_with_meta__(
        cls,
        form_class=None,
        model=None,
        return_field_name=None,
        only_fields=(),
        exclude_fields=(),
        return_field_type=None,
        **options
    ):
        super(GraphqlModelFormDeleteMutation, cls).__init_subclass_with_meta__(
            form_class=form_class,
            model=model,
            return_field_name='is_deleted',
            return_field_type=graphene.Boolean,
            only_fields=only_fields,
            exclude_fields=exclude_fields,
            **options
        )

class FilterConnectionField(DjangoFilterConnectionField):

    permissions = None
    clean_fields = None

    def __init__(self, type, clean_fields=None, **kwargs):
        if hasattr(type, "permission_classes"):
            self.permissions = type.permission_classes()
        else:
            self.permissions = []
        self.clean_fields = clean_fields
        super().__init__(type, **kwargs)
        
    def resolve_queryset(
        self, connection, iterable, info, args, filtering_args, filterset_class, **kwargs
    ):
        if self.clean_fields:
            from_global_id_multiple(self.clean_fields, args)
        if not self.has_permission(info):
            raise Exception("Permission denied.")
        return super().resolve_queryset(
            connection, iterable, info, args, filtering_args, filterset_class, **kwargs
        )

    def has_permission(self, info):
        for permission in self.permissions:
            if not permission.has_permission(info.context):
                return False
        return True


# def get_graphql_response_code(code: str) -> common.StatusCode:
#     return common.StatusCode(code=code, value=STATUS_CODE[code])

# def is_status_code_valid(code: str) -> bool:
#     return not not STATUS_CODE.get(code, None)


# def get_auth_user_from_context(context):
#     if hasattr(context, "user"):
#         return context.user
#     return None

# class FlexDict(dict):
#     def __get__(self, obj, objecttype):


def convert_dict_to_object(dict_obj, name='DictionaryConvertedObject'):
    import types
    obj = types.SimpleNamespace(name=name)
    for k, v in dict_obj.items():
        setattr(obj, k, v)

    def get_func(name):
        return getattr(obj, name, None)
    obj.get = get_func
    return obj