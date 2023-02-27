import logging

# Create logger for the main module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler for the main module logger
file_handler = logging.FileHandler('main.log')
file_handler.setLevel(logging.DEBUG)

# Create a formatter for the main module file handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the main module logger
logger.addHandler(file_handler)

# Create a new logger for a submodule
sub_logger = logging.getLogger('submodule')
sub_logger.setLevel(logging.WARNING)

# Create a console handler for the submodule logger
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

# Create a formatter for the submodule console handler
sub_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(sub_formatter)

# Add the console handler to the submodule logger
sub_logger.addHandler(console_handler)

# Example usage of both loggers
logger.debug('Debug message from main module')
logger.info('Info message from main module')
logger.warning('Warning message from main module')
sub_logger.warning('Warning message from submodule')
sub_logger.error('Error message from submodule')