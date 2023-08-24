import json
import requests

import Base
import Config


class BaseNetDisk:
    """
    The CONSTS need to be set in subclasses and depend on their brand.
    """
    id: int
    path: str
    name: str
    is_dir: bool
    #  These four need to be set in subclasses' __init__

    BRAND: str
    SELECTABLE = True

    __GET_ID_PATH: list[str]
    __GET_PATH_PATH: list[str]
    __GET_NAME_PATH: list[str]
    __GET_IS_DIR_PATH: list[str]

    GET_ITEMS_URL: str
    GET_ITEMS_PARAMS: dict
    GET_ITEMS_PATH: list[str]

    STATUS_CODE_PATH: list[str]
    STATUS_CODE_HANDLE_DICT: dict
    """
    Like this:
    {
        0: 'pass',
        -6: Base.NetDiskAPIError.invalid_user
    }
    """

    object_list: set
    items = set()
    selected = False

    def __init__(self, object: Base.Tree):
        ...

    def get_items_step0(self) -> None:
        self.object_list = self.url_request(
            self.GET_ITEMS_URL,
            self.GET_ITEMS_PARAMS
        ).get_by_path(self.GET_ITEMS_PATH)

    def get_items(self) -> set:
        if self.items:
            return self.items
        self.get_items_step0()

        self.items = set(
            map(
                lambda a: self.__class__(Base.Tree(a)),
                self.object_list
            )
        )

        return self.items

    def show(self) -> set:
        def flush() -> None:
            print(
                '\n\n---------------------------------\n\n' +
                '\n'.join(
                    map(
                        lambda a: (
                                (
                                    (
                                        '8' if pointer == object_list.index(a) else '√'
                                    )
                                    if a in return_objects else
                                    (
                                        'o' if pointer == object_list.index(a) else ' '
                                    )
                                ) +
                                ' ' +
                                a.name +
                                ' - ' +
                                ('DIR' if a.is_dir else 'FIL')
                        ),
                        object_list
                    )
                ),
                '\nPress up/down to choose\n'
                '      s          select\n'
                '      a          select all\n'
                '      enter      go into\n'
                f'      backspace  go back'
            )

        object_list: list[BaseNetDisk] = list(self.get_items())
        pointer = 0
        return_objects = set()
        list_len = len(object_list)
        fls = True
        while True:
            if fls:
                flush()
            fls = True
            pointed_object = object_list[pointer]
            match Base.get_keyboard():
                case 'up':
                    if pointer > 0:
                        pointer -= 1
                case 'down':
                    if pointer < list_len - 1:
                        pointer += 1
                case 's':
                    if not pointed_object.SELECTABLE:
                        Base.show_message("It's not selectable.")
                        continue
                    if redundant_items := (return_objects & pointed_object.items):
                        Base.show_message(f'Redundant items in {pointed_object.name}: '
                                          f'{", ".join(map(lambda a: a.name, redundant_items))}.')
                        continue
                    if pointed_object in return_objects:
                        return_objects.remove(pointed_object)
                        continue
                    return_objects.add(pointed_object)
                    pointed_object.selected = not pointed_object.selected
                case 'a':
                    if not (object_set := set(object_list)) - return_objects:
                        return_objects -= object_set
                        continue
                    return_objects.update(object_set)
                case 'enter':
                    if not pointed_object.is_dir:
                        Base.show_message("It's not a dir.")
                        continue
                    if not pointed_object.get_items():
                        Base.show_message("It's empty.")
                        continue
                    items = pointed_object.show()
                    both = return_objects & items
                    return_objects.update(items - return_objects)
                    return_objects -= both
                    if (pointed_object in return_objects and
                            (redundant_items := (return_objects & pointed_object.items))):
                        Base.show_message(f'Redundant items in {pointed_object.name}: '
                                          f'{", ".join(map(lambda a: a.name, redundant_items))}.')
                        return_objects.remove(pointed_object)
                case 'backspace':
                    return return_objects
                case _:
                    fls = False

    def url_request(self, url: str, params: dict, mode: str = 'get', json_data: dict = None) -> Base.Tree:
        assert mode in ('get', 'post'), f'{mode.capitalize()} is not supported'
        while True:
            with Config.Config('config.json') as config:
                response = eval(f'requests.{mode}')(
                    url,
                    params=params,
                    headers={
                        'Cookie': config.get(self.BRAND)
                    },
                    json=json_data
                )
            response = Base.Tree(json.loads(response.text))

            error_code = response.get_by_path(self.STATUS_CODE_PATH)

            error_message_dict = {
                Base.NetDiskAPIError.invalid_user: f'Try to get the cookie of {self.BRAND} by logining again.',
                Base.NetDiskAPIError.unknown: 'Maybe try again will work?'
            }

            try:
                if (error := self.STATUS_CODE_HANDLE_DICT[error_code]) != 'pass':
                    raise Base.NetDiskAPIError(error_message_dict[error], error)
            except KeyError:
                Base.NetDiskAPIError(
                    f'Maybe try again will work?',
                    Base.NetDiskAPIError.unknown
                ).error_show(self.BRAND)
                continue
            except Base.NetDiskAPIError as error:
                error.error_show(self.BRAND)
                continue

            return response


class BaseNetDiskRoot(BaseNetDisk):
    SHARE_URL: str
    SHARE_PARAMS: Base.Tree
    SHARE_GET_PATH: list[str]
    SHARE_PASSWORD_PATH: list[str]
    SHARE_ITEMS_PATH: list[str]

    items = set()
    share_items = set()

    def __init__(self):
        super().__init__(Base.Tree())
        self.name = self.BRAND
        self.is_dir = True
        self.SELECTABLE = False

    def get_items(self) -> set:
        if self.items:
            return self.items

        self.get_items_step0()

        self.items = set(
            map(
                lambda a: self.__class__.mro()[2](Base.Tree(a)),
                self.object_list
            )
        )

        return self.items

    def show(self):
        self.share_items = super().show()
        if self.share_items:
            return {self}
        return set()

    def share(self, password: str) -> str:
        assert len(password) == 4, 'Error: the length of the password must be 4'
        assert password.isalnum(), 'Error: the allowed are alphabets and numbers'

        self.SHARE_PARAMS.set_by_path(self.SHARE_PASSWORD_PATH, password)
        self.SHARE_PARAMS.set_by_path(self.SHARE_ITEMS_PATH, self.share_items)

        return self.url_request(
            self.SHARE_URL,
            self.SHARE_PARAMS
        ).get_by_path(self.SHARE_GET_PATH)


class BaiduNetDisk(BaseNetDisk):
    id: int
    path: str
    name: str
    is_dir: bool

    BRAND = 'BaiduNetDisk'

    __GET_ID_PATH = ['fs_id']
    __GET_PATH_PATH = ['path']
    __GET_NAME_PATH = ['server_filename']
    __GET_IS_DIR_PATH = ['isdir']

    GET_ITEMS_URL = 'https://pan.baidu.com/api/list'
    GET_ITEMS_PATH = ['list']

    STATUS_CODE_PATH = ['errno']
    STATUS_CODE_HANDLE_DICT = {
        0: 'pass',
        -6: Base.NetDiskAPIError.invalid_user,
        2: ''
    }

    def __init__(self, object):
        self.id = object.get_by_path(self.__GET_ID_PATH)
        self.path = object.get_by_path(self.__GET_PATH_PATH)
        self.name = object.get_by_path(self.__GET_NAME_PATH)
        self.is_dir = object.get_by_path(self.__GET_IS_DIR_PATH)
        self.GET_ITEMS_PARAMS = Base.Tree(
            {
                'dir': self.path
            }
        )
        super().__init__(object)


class BaiduNetDiskRoot(BaseNetDiskRoot, BaiduNetDisk):
    SHARE_URL = 'https://pan.baidu.com/share/set'
    SHARE_PARAMS = Base.Tree(
        {
            'schannel': 4
        }
    )
    SHARE_GET_PATH = ['link']
    SHARE_PASSWORD_PATH = ['pwd']
    SHARE_ITEMS_PATH = ['fid_list']

    def __init__(self):
        super().__init__()
        self.path = '/'

    def share(self, password: str) -> str:
        self.share_items = str(
            list(
                map(
                    lambda a: a.id,
                    self.share_items
                )
            )
        )
        return super().share(password)


class QuarkCloudDrive(BaseNetDisk):
    id: str
    path: str
    name: str
    is_dir: bool

    BRAND = 'QuarkCloudDrive'

    __GET_ID_PATH = ['fid']
    __GET_NAME_PATH = ['file_name']
    __GET_IS_DIR_PATH = ['dir']

    GET_ITEMS_URL = 'https://drive-pc.quark.cn/1/clouddrive/file/sort'
    GET_ITEMS_PATH = ['data', 'list']

    STATUS_CODE_PATH = ['code']
    STATUS_CODE_HANDLE_DICT = {
        0: 'pass',
        31001: Base.NetDiskAPIError.invalid_user
    }

    def __init__(self, object):
        self.id = object.get_by_path(self.__GET_ID_PATH)
        self.name = object.get_by_path(self.__GET_NAME_PATH)
        self.is_dir = object.get_by_path(self.__GET_IS_DIR_PATH)
        self.GET_ITEMS_PARAMS = {
            'pr': 'ucpro',
            'fr': 'pc',
            'pdir_fid': self.id
        }
        super().__init__(object)


class QuarkCloudDriveRoot(BaseNetDiskRoot, QuarkCloudDrive):
    def __init__(self):
        super().__init__()
        self.id = '0'

    def share(self, password: str) -> str:
        self.share_items = list(
            map(
                lambda a: a.id,
                self.share_items
            )
        )
        task_id = self.url_request(
            'https://drive-pc.quark.cn/1/clouddrive/share',
            {
                'pr': 'ucpro',
                'fr': 'pc'
            },
            mode='post',
            json_data={
                'expired_type': 1,
                'fid_list': self.share_items,
                'passcode': password,
                'url_type': 2
            }
        )['data']['task_id']

        retry_index = 0
        while True:
            share_id = self.url_request(
                'https://drive-pc.quark.cn/1/clouddrive/task',
                Base.Tree(
                    {
                        'pr': 'ucpro',
                        'fr': 'pc',
                        'task_id': task_id,
                        'retry_index': retry_index
                    }
                )
            )
            retry_index += 1
            if share_id := share_id['data'].get('share_id', share_id):
                break

        return self.url_request(
            'https://drive-pc.quark.cn/1/clouddrive/share/password',
            Base.Tree(
                {
                    'pr': 'ucpro',
                    'fr': 'pc'
                }
            ),
            mode='post',
            json_data={
                'share_id': share_id
            }
        )['data']['share_url']
