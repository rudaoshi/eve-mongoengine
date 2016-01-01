# -*- coding: utf-8 -*-

"""
    eve_mongoengine.validation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module implements custom validator based on
    :class:`eve.io.mongo.validation`, which is cerberus-validator extension.

    The purpose of this module is to enable validation for special mongoengine
    fields.

    :copyright: (c) 2014 by Stanislav Heller.
    :license: BSD, see LICENSE for more details.
"""

from flask import current_app as app
from mongoengine import ValidationError, FileField

from eve.io.mongo.validation import Validator
from eve_mongoengine._compat import iteritems
from werkzeug.datastructures import FileStorage
from mongoengine.fields import GridFSProxy
from bson import ObjectId
import pymongo

class EveMongoengineValidator(Validator):
    """
    Helper validator which adapts mongoengine special-purpose fields
    to cerberus validator API.
    """
    def validate(self, document, schema=None, update=False, context=None):
        """
        Main validation method which simply tries to validate against cerberus
        schema and if it does not fail, repeats the same against mongoengine
        validation machinery.
        """
        # call default eve's validator
        if not Validator.validate(self, document, schema, update, context):
            return False

        # validate using mongoengine field validators
        if self.resource and context is None:
            model_cls = app.data.models[self.resource]

            # We must translate any database field names to their corresponding
            # MongoEngine names before attempting to validate them.
            translate = lambda x: model_cls._reverse_db_field_map.get(x, x)
            document = {translate(k): document[k] for k in document}

            doc = model_cls(**document)
            # rewind all file-like's
            for attr, field in iteritems(model_cls._fields):
                if (isinstance(field, FileField) and
                            attr in document and
                            not isinstance(document[attr], GridFSProxy)):
                    document[attr].stream.seek(0)

            try:
                doc.validate()
            except ValidationError as e:
                for field_name, error in e.errors.items():
                    self._error(field_name, str(e))
                return False

        return True

    def _validate_type_dynamic(self, field, value):
        """
        Dummy validation method just to convince cerberus not to validate that
        value.
        """
        pass

    def _validate_type_media(self, field, value):
        """ Enables validation for `media` data type.

        :param field: field name.
        :param value: field value.

        .. versionadded:: 0.3
        """
        if (not isinstance(value, FileStorage) and
                not isinstance(value, GridFSProxy) and
                not isinstance(value, ObjectId)):
            self._error(field, "file was expected, got '%s' instead." % value)
