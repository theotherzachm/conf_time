from copy import copy
from jinja2 import Environment, FileSystemLoader
from ncclient import manager
from ncclient.xml_ import new_ele


def detect(conn_params):
    '''
    Figure out server capabilities and return the appropriate
    device_params.
    '''
    with manager.connect(**conn_params) as conn:
        capabilities = conn.server_capabilities
        if ":candidate" in capabilities:
            # Probably junos.
            return {'name': 'junos'}
        else:
            # If :candidate URI is missing, assume
            # nexus. Some logic can be added to distinguish
            # between IOS-XE/R, NX-OS, and other vendors.
            return {'name': 'nexus'}


class Junos(object):
    '''
    Junos device class. NETCONF derived attributes are a list
    of tuples defined in attributes. Mutable attributes have an
    xpath query accompanying them. Immutable ones are None, and
    correspond with an object attribute that returns their value.
    '''

    class Cache:
        '''
        Serves as a cache object to store the initial state of
        outer object as well as the config returned by
        _query_config and inventory.
        '''
        init_state = None
        inventory = None
        config = None

    attributes = [
        ('hostname', '//host-name'),
        ('ntp_servers', '//ntp/server/name'),
        ('snmp_communities', '//snmp/community/name'),
        ('serial', None),
        ('model', None),
        ('ifaces', None),
    ]

    def __init__(self, conn_params):
        self._conn = self._setup_conn(conn_params)
        self._get_init_values()
        self.Cache.init_state = copy(self)

    def __iter__(self):
        for i in self.attributes:
            yield (i[0], getattr(self, i[0]))

    def __str__(self):
        ret = [
            "{}={}".format(i[0], getattr(self, i[0]))
            for i in self
        ]
        return ', '.join(ret)

    def _get_init_values(self):
        '''
        Populates mutable attributes on init.
        '''
        for i in self.attributes:
            if i[1]:
                query = self._query(
                    cache_attr='config',
                    xpath=i[1],
                    nc_query=self._conn.get_config(source='running')
                )
                setattr(self, i[0], query)

    def _setup_conn(self, conn_params):
        '''
        Returns a connection or test data
        based on whether a test is being run.
        '''
        if type(conn_params) is dict:
            return manager.connect(**conn_params)
        else:
            return conn_params

    def _query(self, cache_attr=None, xpath=None, nc_query=None):
        '''
        Gets nc_query or looks up the contents of cache based
        on cache_attr. Takes cache or lookup and runs xpath
        search and returns contents of element(s).
        '''
        if not cache_attr and xpath and nc_query:
            raise TypeError("Missing keyword arguements.")
        query = getattr(self.Cache, cache_attr, None)
        if not query:
            query = nc_query
        ret = query.xpath(xpath)
        if ret:
            if len(ret) > 1:
                return sorted([i.text for i in ret])
            else:
                return ret[0].text
        else:
            return None

    def _edit_config(self, config):
        '''
        Locks running configuration for editing and sends
        contents of config.
        '''
        with self._conn.locked(target='running'):
            return self._conn.edit_config(config=config)

    def commit(self):
        '''
        Commits config.
        '''
        return self._conn.commit()

    def _serialize(self, attr=None, values=None):
        '''
        Returns rendered jinja template based on file derived
        from attrname.j2 existing in templates directory. Values is a
        string or iterable passed to the jinja template.
        '''
        if not attr:
            raise TypeError('Attr is required.')
        env = Environment(loader=FileSystemLoader(['templates']))
        template = "{}.j2".format(attr)
        return env.get_template(template).render({'values': values})

    def update(self, edit=True, commit=False):
        '''
        Compares current state of attributes to the copy saved
        at init. Then determines which attributes differ and
        sends the appropriate xml template.
        '''
        cache = self.Cache.init_state
        if str(self) != str(cache):
            for i in self:
                if i[1] != getattr(cache, i[0]):
                    xml = self._serialize(
                        attr=i[0],
                        values=i[1]
                    )
                    if edit:
                        if self._edit_config(xml):
                            return True
                    if commit:
                        if self.commit():
                            return True
                    else:
                        return xml
        return False

    def close(self):
        if self._conn.close_session():
            return True

    @property
    def serial(self):
        '''
        Returns the chassis serial number.
        '''
        xpath = 'chassis-inventory/chassis/serial-number[1]'
        nc_query = self._conn.rpc(
            new_ele('get-chassis-inventory')
        )
        query = self._query(
            cache_attr='inventory',
            xpath=xpath,
            nc_query=nc_query
        )
        return query

    @property
    def model(self):
        '''
        Returns the chassis description.
        '''
        xpath = 'chassis-inventory/chassis/description[1]'
        nc_query = self._conn.rpc(
            new_ele('get-chassis-inventory')
        )
        query = self._query(
            cache_attr='inventory',
            xpath=xpath,
            nc_query=nc_query
        )
        return query

    @property
    def ifaces(self):
        '''
        Parses and returns the output of show interfaces terse.
        '''
        node = new_ele('command', {'format': 'xml'})
        node.text = 'show interface terse'
        query = self._conn.rpc(node)
        ret = [i.text.replace('\n', '') for i in query.xpath('//name')]
        return ret
