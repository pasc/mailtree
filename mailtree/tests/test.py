# -*- coding: utf-8 -*-

from mailtree import MailTreeNode, MailTree
from mailtree import parse_message_ids

from email.message import Message

import unittest

from mock import Mock

class TestMailTreeNode(unittest.TestCase):

    def setUp(self):
        self.msg = Message()
        self.msg.set_payload("my payload")
        self.msg['From'] = 'From test <from@example.com>'
        self.msg['Message-Id'] = '<abcd@example.com>'
        self.msg['Subject'] = 'This is an example'

    def test_mail_tree_node(self):
        mtn = MailTreeNode('abcde')

        tree = Mock()
        mtn.hydrate (self.msg, tree)
        
        self.assertEqual(mtn.author, 'From test <from@example.com>')
        self.assertEqual(mtn.subject, 'This is an example')

    def test_mail_tree_node_with_reply(self):
        mtn = MailTreeNode('abcde')

        self.msg['In-Reply-To'] = "<efg@example.com>"

        tree = Mock()
        tree.nodes = {'efg@example.com': Mock()}
        mtn.hydrate (self.msg, tree)
        
        self.assertEqual(mtn.author, 'From test <from@example.com>')
        self.assertEqual(mtn.subject, 'This is an example')

        tree.nodes['efg@example.com'].children.append.assert_called_once_with(mtn)


class TestMailTree(unittest.TestCase):
    def test_add_author(self):
        mt = MailTree('abc@efg')
        mt.add_author('My Name Is <name@example.com>')

        self.assertEqual(mt.authors, ['My Name Is <name@example.com>'])

    def test_add_multi_authors(self):
        mt = MailTree('abc@efg')
        mt.add_author('author1@example.com')
        mt.add_author('author2@example.com')
        mt.add_author('author1@example.com')

        self.assertEqual(mt.authors, ['author1@example.com', 'author2@example.com'])

    def test_add_encoded_author(self):
        mt = MailTree('abc@efg')

        mt.add_author('=?utf-8?b?xZrDtsacxJMgxYXEg23EkyA8bmFtZUBleGFtcGxlLmNvbT4=?=')

        self.assertEqual(mt.authors, [u'ŚöƜē Ņămē <name@example.com>'])

class TestMessageIDParser(unittest.TestCase):
    def test_simple(self):
        ids = "<abc@efg>"
        ret = parse_message_ids(ids)

        self.assertTrue(isinstance(ret, list))
        self.assertEqual(ret, ['abc@efg'])

    def test_multiple(self):
        ids = "<abc@efg> <efg@efg>\n\t<jhk@efg>"
        ret = parse_message_ids(ids)

        self.assertTrue(isinstance(ret, list))
        self.assertEqual(ret, ['abc@efg', 'efg@efg', 'jhk@efg'])

    def test_multiple_with_comment(self):
        ids = "<abc@efg> (This is a comment) <blah@narf>"
        ret = parse_message_ids(ids)

        self.assertTrue(isinstance(ret, list))
        self.assertEqual(ret, ['abc@efg', 'blah@narf'])

    def test_multiple_no_gap(self):
        ids = "<abc@efg><efg@efg>"
        ret = parse_message_ids(ids)

        self.assertTrue(isinstance(ret, list))
        self.assertEqual(ret, ['abc@efg', 'efg@efg'])

