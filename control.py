import subprocess
import os

import yaml

file_path_list = os.path.normpath(__file__).split('/')
PARSERS_PATH = '/' + os.path.join(*file_path_list[:-2])
INTERPRETER_PATH = os.path.join(PARSERS_PATH, *['env', 'bin', 'python3'])


class Control():
    def __init__(self):
        self.config = self.load_configs()
        self.status = {}
        self.list_of_active_parsers = None
        self.list_of_active_docker_containers = None
        self.collect_status()

    def check_statuses(self):
        self.list_of_active_parsers = self.parsers_status()
        self.list_of_active_docker_containers = self.docker_status()

    def collect_status(self):
        self.check_statuses()
        for category in self.config.keys():
            for spider in self.config[category].keys():
                if spider == 'common':
                    continue

                name = f'{category}.{spider}'
                status = True if name in self.list_of_active_parsers else False
                if status:
                    pid = self.list_of_active_parsers[name]
                else:
                    pid = None

                try:
                    previous_status = self.status[category][spider].get('status')
                except KeyError:
                    previous_status = None

                try:
                    previous_log_file = self.status[category][spider].get('log_file')
                except KeyError:
                    previous_log_file = None

                if previous_status is None or previous_status != status or previous_log_file is None:
                    log_file_path = self.get_log_path(category, name)
                    try:
                        self.status[category] = {**self.status[category],
                                                 **{
                                                     spider:
                                                         {
                                                             'status': status,
                                                             'log_file': log_file_path,
                                                             'pid': pid
                                                         }
                                                 }
                                                 }
                    except KeyError:
                        self.status = {**self.status,
                                       **{
                                           category:
                                               {
                                                   spider:
                                                       {
                                                           'status': status,
                                                           'log_file': log_file_path,
                                                           'pid': pid
                                                       }
                                               }
                                       }
                                       }

        self.status['docker'] = {}
        for docker_name in self.list_of_active_docker_containers:
            status = bool(self.list_of_active_docker_containers[docker_name])
            if status:
                id_list = self.list_of_active_docker_containers[docker_name]
                if len(id_list) > 1:
                    number = 1
                    for id in id_list:
                        docker_name = f'{docker_name} {number}'
                        number += 1
                        self.status['docker'] = {**self.status['docker'],
                                                 **{
                                                     docker_name:
                                                         {
                                                             'status': status,
                                                             'log_file': None,
                                                             'pid': id
                                                         }
                                                 }
                                                 }
                else:
                    self.status['docker'] = {**self.status['docker'],
                                             **{
                                                 docker_name:
                                                     {
                                                         'status': status,
                                                         'log_file': None,
                                                         'pid': id_list[0]
                                                     }
                                             }
                                             }
            else:
                self.status['docker'] = {**self.status['docker'],
                                         **{
                                             docker_name:
                                                 {
                                                     'status': status,
                                                     'log_file': None,
                                                     'pid': None
                                                 }
                                         }
                                         }


    @staticmethod
    def load_configs():
        # check hostname
        f = os.popen('hostname')
        hostname = f.readlines()
        hostname = hostname[0].replace('\n', '')

        # select config file
        if hostname == 'pnz-pythonpars':
            config_file_name = 'pnz-configs.yaml'
        elif hostname in ['otc-pythonpars', 'x']:		#	local settings
        # elif hostname == 'otc-pythonpars':
            config_file_name = 'otc-configs.yaml'
        else:
            raise ValueError(f"I can't select a configs file for hostname '{hostname}'")
        path = os.path.join(PARSERS_PATH, config_file_name)

        with open(path) as f:
            configs = yaml.safe_load(f)
            configs = {x: y for x, y in configs.items() if x in ['purchases', 'offers', 'other']}
        return configs

    @staticmethod
    def start_spider(category, spider_name):
        command = f'if [ $(pgrep -af {category} | grep {spider_name} | wc -l) -eq 0 ]; ' \
                  f'then {INTERPRETER_PATH} scrapy crawl {category}.{spider_name} &>/dev/null & else :; fi'
        subprocess.run(command, shell=True)

    @staticmethod
    def stop_spider(pid):
        command = f'kill {pid}'
        subprocess.run(command, shell=True)

    @staticmethod
    def parsers_status():
        command = ['pgrep -af scrapy']
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True, encoding='utf-8')
        shell_result = result.stdout

        result_rows = shell_result.split('\n')
        search_list = ['other.', 'offers.', 'purchases.']
        result = {}
        for row in result_rows:
            split_row = row.split(' ')
            pid = split_row[0]
            for value in split_row:
                for search in search_list:
                    if search in value:
                        result[value] = pid

        return result

    @staticmethod
    def docker_status():
        command = ['docker ps']
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True, encoding='utf-8')
        shell_result = result.stdout
        rows = shell_result.split('\n')

        result = {
            'selenium': None,
            'selenium_bankrot': None,
            'tor': None,
            'splash': None,
        }
        for row in rows:
            if not row:
                continue
            docker_name = row.split('/tcp')[-1].strip()
            docker_id = row.split(' ')[0].strip()
            if docker_name in result.keys():
                result[docker_name].append(docker_id)
            else:
                result[docker_name] = [docker_id]

        return result

    @staticmethod
    def get_log_path(category, name):
        path = os.path.join(PARSERS_PATH, 'logs', category, name)
        try:
            files = os.listdir(path)
            paths = [os.path.join(path, basename) for basename in files]
            latest_log_file_path = max(paths, key=os.path.getctime)
            return latest_log_file_path
        except (FileNotFoundError, ValueError):
            return None

# example:

# shell_result = """
# 13536 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl other.bankrot
# 24661 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl offers.ppm
# 24710 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl offers.sberb2b
# 39334 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl other.bo_nalog
# 53185 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl other.eruz
# 53229 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl other.sber_223_protocols
# 54115 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl offers.tenderpro
# 59034 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl purchases.roseltorg
# 59082 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl purchases.etprf
# 59298 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl offers.napolke
# 59338 /opt/parsers/env/bin/python3 /opt/parsers/env/bin/scrapy crawl other.nostroy
# """
#
# result = ['other.bankrot', 'offers.ppm', 'offers.sberb2b', 'other.bo_nalog', 'other.eruz', 'other.sber_223_protocols',
#           'offers.tenderpro', 'purchases.roseltorg', 'purchases.etprf', 'offers.napolke', 'other.nostroy']
