import os
import json
import attrs
import logging

import papermill
import jsonschema
from tabulate import tabulate

logger = logging.getLogger(__name__)

"""
Loads the .ipynb jsonschema for validation purposes (TBD).
"""
LOCAL_PATH = os.path.dirname(os.path.realpath(__file__))
SCHEMA_LIST = [os.path.join(LOCAL_PATH,
                            'schemas/nbformat.v4.{v}.schema.json'.format(v=i)) for i in range(0, 6)]


class ApplicationParameter(object):
    def __init__(self, papermill_info):

        self.papermill_info = papermill_info

    @property
    def name(self):
        return self.papermill_info['name']

    @property
    def inferred_type(self):

        if self.papermill_info['inferred_type_name'] != 'None':
            return self.papermill_info['inferred_type_name']
        else:
            return type(self.default).__name__

    @property
    def default(self):
        return eval(self.papermill_info['default'])

    @property
    def help(self):
        return self.papermill_info['help'] 

    @property
    def cwl_type(self):
        """Attempts to convert the inferred type to an equivalent CWL type.

        Otherwise, checks if a given key's default value is a string or can be converted to a float."""

        inferred_type = self.inferred_type

        # Use papermill version of default since we will massage default into 
        # a Python type
        default_val = self.papermill_info['default']

        inferred_type = inferred_type.lower()
        convert_dict = {
            'string': ['stage_in', 'stage-in', 'string'],
            'File': ['stage_out', 'stage-out', 'file'],
            'int': ['int', 'integer'],
            'boolean': ['bool', 'boolean'],
            'float': ['float'],
            'double': ['double'],
            'Directory': ['directory'],
            'Any': ['any'],
            'null': ['nonetype'],
        }
        for key in convert_dict:
            if inferred_type in convert_dict[key]:
                return key

        if default_val.find('"') != -1 or default_val.find('\'') != -1:
            return 'string'
        key_type = 'Any'
        try:
            temp = float(default_val)
            key_type = 'float'
        except ValueError:
            pass
        return key_type

class ApplicationError(Exception):
    pass

@attrs.define
class ApplicationInterface(object):
    "Defines the interface expected for parsed applications"

    # Parameters labeled for supplying the stage in/stage out STAC collection file names
    # The stage in collection file is written by the stage in step
    # The stage out collection file is written by the application
    stage_in_param: ApplicationParameter = None
    stage_out_param: ApplicationParameter = None

    # Free arguments that are papermill parameters not associated with stage
    arguments: list[ApplicationParameter] = []

class ApplicationNotebook(ApplicationInterface):
    """Defines a parsed Jupyter Notebook read as a JSON file."""

    def __init__(self, notebook_filename):

        super().__init__()

        # Parsed notebook
        self.notebook = {}

        # All parameters parsed from the notebook
        self.notebook_parameters = []

        self.filename = notebook_filename
        self.parse_notebook(notebook_filename)

    def parse_notebook(self, notebook_filename):
        """Parses validate notebook_filename as a valid, existing Jupyter Notebook to
        ensure no exception is thrown.
        """
        if not os.path.exists(notebook_filename):
            raise ApplicationError(f"Could not find notebook file: {notebook_filename}")

        logger.info(f'Reading notebook: "{notebook_filename}"')
        with open(notebook_filename, 'r') as f:
            self.notebook = json.load(f)

        # Validate the notebook using the list of supported v4.X schemas.
        logger.debug(f'Validating {notebook_filename} as a valid v4.0 - v4.5 Jupyter notebook')
        validation_success = False
        for fname in SCHEMA_LIST:
            if os.path.exists(fname):
                try:
                    with open(fname, 'r') as f:
                        schema = json.load(f)
                        jsonschema.validate(
                            instance=self.notebook, schema=schema)
                        logger.debug(f'Successfully validated using "{os.path.basename(fname)}"')
                        validation_success = True
                        break
                except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
                    logger.error(f'Failed validation using "{os.path.basename(fname)}"')
                    continue
            else:
                logger.error(f'Validation file "{fname}" does not exist.')

        if not validation_success:
            raise ApplicationError(f'Failed to validate "{notebook_filename}" as a v4.0 - v4.5 Jupyter Notebook...')

        # Inspect notebook parameters using papermill and parse them into a list.
        self.notebook_parameters = []
        for papermill_param in papermill.inspect_notebook(notebook_filename).values():
            app_param = ApplicationParameter(papermill_param)
            self.notebook_parameters.append(app_param)

            inferred_type = app_param.inferred_type

            if inferred_type in ['stage-in', 'stage_in']:
                if self.stage_in_param is None:
                    self.stage_in_param = app_param
                else:
                    raise ApplicationError(f"Only one stage-in parameter allowed per notebook")

            elif inferred_type in ['stage-out', 'stage_out']:
                if self.stage_out_param is None:
                    self.stage_out_param = app_param
                else:
                    raise ApplicationError(f"Only one stage-out parameter allowed per notebook")
            else:
                self.arguments.append(app_param)

    def parameter_summary(self):

        headers = [ 'name', 'inferred_type', 'cwl_type', 'default', 'help' ]

        # Build up rows of the table using the header values as the columns
        table_data = []
        for app_param in self.notebook_parameters:
            table_row = []
            for column_name in headers:
                table_row.append(getattr(app_param, column_name))
            table_data.append(table_row)

        return tabulate(table_data, headers=headers)
