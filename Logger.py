from dataclasses import dataclass

import click


@dataclass
class Logger:
    INFO: int = 0
    WARNING: int = 1
    ERROR: int = 2
    logLevel: int = 2
        
    def log(self, message: str, level: int = 0):
        if level >= self.logLevel:
            click.echo(message)