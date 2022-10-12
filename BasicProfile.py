#!/usr/bin/python3
# pylint: disable=wrong-import-position, invalid-name
import logging
import os
from json import loads
from platform import system
from subprocess import CalledProcessError

from Common import (Filespace, execute_command, FILESPACE_NAME, PROVIDER, PROTOCOL,
                    ACCESS_KEY, SECRET_KEY, BUCKET_NAME, REGION, ENDPOINT)

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
TEST_DURATION = 20  # seconds


class StorePerfWrapper:  # pylint: disable=too-few-public-methods
    def __init__(self, fs):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.filespace = fs

        self.path = ROOT_PATH + (r'\Binaries\StorePerf.exe' if system() == 'Windows' else '/Binaries/StorePerf')

        if not os.path.isfile(self.path) or not os.access(self.path, os.X_OK):
            raise ValueError("Couldn't find StorePerf binary or it's not executable")

    def _execute_command(self, *arguments):
        command = self.path + ' --' + self.filespace.protocol + ' --endpoint ' + self.filespace.endpoint + \
                 ' --access-key ' + self.filespace.access_key + ' --secret-key ' + self.filespace.secret_key + \
                 ' --provider ' + self.filespace.provider + ' --bucket-name ' + self.filespace.bucket_name + \
                 ' --json --log-level fatal '

        if self.filespace.region:
            command += ' --region ' + self.filespace.region + ' '

        command += ' '.join(str(a) for a in arguments)
        return execute_command(self.logger, command)

    def test(self, size, io_count):
        try:
            output = self._execute_command('--multi-object', '--size', size + 'KiB', '--ios', io_count, '--time', TEST_DURATION)
        except CalledProcessError as exc:
            self.logger.error('Error during execution, output: %s', exc.output.decode())
            return {}
        else:
            res = loads(output)
            self.logger.debug('%s', output)
            return res


def format_result(result):
    rtt = int(result['rtt']['averageRTT'] * 1000)
    speedDown = round(result['download']['throughput'] / 125000, 2)
    latencyDown = int(result['download']['latency'] * 1000)
    speedUp = round(result['upload']['throughput'] / 125000, 2)
    latencyUp = int(result['upload']['latency'] * 1000)
    return f'{rtt};{speedDown};{latencyDown};{speedUp};{latencyUp}'



if __name__ == '__main__':
    logName = os.path.basename(__file__).split('.')[0] + '.log'
    logging.basicConfig(filename=logName, level=logging.DEBUG, format='%(asctime)s | %(levelname).1s | %(name)s | %(message)s')

    if not all([a for a in (FILESPACE_NAME, PROVIDER, PROTOCOL, ACCESS_KEY, SECRET_KEY, BUCKET_NAME, ENDPOINT)]):
        raise ValueError('All constants must be entered')

    STORE = StorePerfWrapper(Filespace(FILESPACE_NAME, PROVIDER, PROTOCOL, ACCESS_KEY, SECRET_KEY, BUCKET_NAME, REGION, ENDPOINT))

    for io_size in ['1', '257', '1000', '4000']:
        for io_count in ['1', '2', '4', '8', '16', '32', '64', '128', '256']:
            res = STORE.test(io_size, io_count)
            print(f'{io_size};{io_count};{format_result(res)}')
