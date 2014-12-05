#!/usr/bin/env python
"""Unit tests for :mod:`katello_rapidnode`."""
import katello_rapidnode
import unittest

from sys import version_info
if version_info[0] == 2:
    import mock  # (import-error) pylint:disable=F0401
else:
    from unittest import mock  # (no-name-in-module) pylint:disable=E0611


class ParentGetCapsulesTestCase(unittest.TestCase):
    """Tests for :func:`katello_rapidnode.parent_get_capsules`."""

    def test_1_capsule(self):
        """What happens when the server returns info about one capsule?"""
        with mock.patch.object(
            katello_rapidnode,
            'paramiko_exec_command'
        ) as cmd:
            cmd.return_value = (
                b'Id,Name,URL\n1,example.com,https://example.com:9090\n',
                b''
            )
            self.assertEqual(
                katello_rapidnode.parent_get_capsules(),
                ['1,example.com,https://example.com:9090'],
            )

    def test_2_capsules(self):
        """What happens when the server returns info about two capsules?"""
        with mock.patch.object(
            katello_rapidnode,
            'paramiko_exec_command'
        ) as cmd:
            cmd.return_value = (
                # Note the implicit line joins.
                b'Id,Name,URL\n'
                b'1,example1.com,https://example1.com:9090\n'
                b'2,example2.com,https://example2.com:9090\n',
                b''
            )
            self.assertEqual(
                katello_rapidnode.parent_get_capsules(),
                [
                    '1,example1.com,https://example1.com:9090',
                    '2,example2.com,https://example2.com:9090',
                ],
            )


if __name__ == '__main__':
    unittest.main()
