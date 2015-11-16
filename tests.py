import unittest
from ncclient.xml_ import NCElement
from ncclient import manager
from conf_time.device import Junos


class TestData(object):
    def _test_data(self, path):
        with open(path, 'r') as f:
            reply = f.read()
        return NCElement(
            reply,
            manager.make_device_handler({'name': 'junos'}).transform_reply()
        )

    def rpc(self, element):
        if 'get-chassis-inventory' in element.tag:
            return self._test_data('test_data/get_chassis_inventory.xml')
        if 'command' in element.tag and 'show interface terse' in element.text:
            return self._test_data('test_data/sh_int_terse.xml')

    def get_config(self, source):
        return self._test_data('test_data/config.xml')


class Tests(unittest.TestCase):

    def setUp(self):
        self.conn = Junos(TestData())

    def test_get_serial(self):
        self.assertTrue(self.conn.serial)
        self.assertEqual(self.conn.serial, '98f086798881')

    def test_get_model(self):
        self.assertTrue(self.conn.model)
        self.assertEqual(self.conn.model, 'FIREFLY-PERIMETER')

    def test_get_ifaces(self):
        self.assertTrue(self.conn.ifaces)

    def test_get_hostname(self):
        self.assertTrue(self.conn.hostname)
        self.assertEqual(self.conn.hostname, 'vsrx')

    def test_get_ntp(self):
        ntp_list = [
            '10.0.2.1',
            '10.0.2.2',
        ]
        self.assertTrue(self.conn.ntp_servers)
        self.assertEqual(self.conn.ntp_servers, sorted(ntp_list))

    def test_get_snmp_comms(self):
        comm_list = [
            'public',
            'private',
        ]
        self.assertTrue(self.conn.snmp_communities)
        self.assertEqual(self.conn.snmp_communities, sorted(comm_list))

    def test_update(self):
        self.conn.ntp_servers = [
            '10.0.2.1',
            '10.0.2.2',
            '10.0.2.3',
        ]
        self.assertTrue(self.conn.update(edit=False))


if __name__ == '__main__':
    unittest.main()
