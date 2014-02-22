import mailbox
import string

from email.header import decode_header

class MailTreeNode:
    def __init__(self, message_id):
        self.isEmpty = True
        self.children = []
        self.message_id = message_id

    def hydrate(self, message, tree):
        self.author = get_header(message.get('From', ''))
        self.subject = get_header(message.get('Subject'))
        if message.get('In-reply-to'):
            in_reply_to = parse_message_ids(message.get('In-Reply-To'))
            if len(in_reply_to):
                tree.nodes[in_reply_to[0]].children.append(self)

        self.isEmpty = False

    def __repr__(self):
        return "<MailTreeNode: %s>" % self.message_id


class MailTree:
    def __init__(self, message_id, message = None):
        self.parent = MailTreeNode(message_id)
        self.nodes = {message_id: self.parent}
        self.authors = []
        self.message_id = message_id
        if message:
            self.hydrate(message)

    def hydrate(self, message, references=None):
        if references is None:
            references = parse_message_ids(message.get('References', ""))

        for ref in references:
            if ref not in self.nodes:
                self.nodes[ref] = MailTreeNode(ref)

        if self.parent.isEmpty:
            self.parent.hydrate(message, self)

        mid = parse_message_ids(message.get('Message-Id'))
        if len(mid) > 0:
            self.message_id = mid[0]

        self.add_author(message.get('From'))

    def add_author(self, author):
        formatted = get_header(author)
        if formatted not in self.authors:
            self.authors.append(formatted)

    def graft(self, other):
        for author in other.authors:
            if author not in self.authors:
                self.authors.append(author)

        for node in other.nodes:
            if node not in self.nodes:
                self.nodes[node] = other.nodes[node]
            elif not other.nodes[node].isEmpty:
                self.nodes[node] = other.nodes[node]

            for child in other.nodes[node].children:
                if child not in self.nodes[node].children:
                    self.nodes[node].children.append(child)

        other.message_id = self.message_id

    def addChild(self, message, references=None):
        self.add_author(message.get('From'))

        for ref in references or []:
            if ref not in self.nodes:
                self.nodes[ref] = MailTreeNode(ref)

        mid = message.get('Message-id')
        mid = parse_message_ids(mid)[0]
        if mid not in self.nodes:
            self.nodes[mid] = MailTreeNode(mid)
        
        if self.nodes[mid].isEmpty:
            self.nodes[mid].hydrate(message, self)

    def addTree(self, tree):
        """This is dead code"""
        self.children.append(tree.parent)
        for author in tree.authors:
            if author not in self.authors:
                self.authors.append(author)

    def walk_tree(self):
        """Go through the list of messages in this email tree depth-first

        TODO:  it may be possible for orphan nodes to exist.
        """
        stack = [self.parent]

        while stack != []:
            current = stack.pop()
            yield current

            for x in current.children:
                stack.insert(0, x)



class MailForest(dict):
    def __init__(self):
        self.trees = {}
        self.keys = {}

    def pruned_trees(self):
        trees = {}
        for k in self.keys():
            if self[k].message_id == k:
                trees[k] = self[k]

        return trees

    def parent_key(self, key):
        while key != self.keys[key]:
            key = self.keys[key]

        return key

    def __getitem__(self, key):
        if key not in self.keys:
            raise IndexError
        key = self.parent_key(key)

        return self.trees[key]

    def __len__(self):
        return len(self.trees)

    def fill_tree(self, box):
        for m in box:
            msg_id = m.get('Message-id')
            msg_id = parse_message_ids(msg_id)[0]

            references = parse_message_ids(m.get('References', ''))
            references.extend(parse_message_ids(m.get('In-Reply-To', '')))

            if len(references) > 0:
                tree_key = references[0]
                if tree_key in self.keys:
                    tree_key = self.parent_key(tree_key)

                if tree_key not in self.trees:
                    self.trees[tree_key] = MailTree(tree_key)

                for ref in references:
                    if ref not in self.keys:
                        self.keys[ref] = tree_key

                if msg_id not in self.keys:
                    self.keys[msg_id] = tree_key
                    self.trees[tree_key].addChild(m, references)
                elif msg_id in self.trees:
                    self.trees[msg_id].hydrate(m, references)
                    self.trees[tree_key].graft(self.trees[msg_id])
                    del self.trees[msg_id]
                    self.keys[msg_id] = tree_key
                else:
                    self.trees[tree_key].addChild(m, references)

            else:
                self.keys[msg_id] = msg_id
                if msg_id in self.trees:
                    self.trees[msg_id].hydrate(m)
                else:
                    self.trees[msg_id] = MailTree(msg_id, m)

def get_header(header):
    dh = decode_header(header)
    return ''.join([ unicode(t[0], t[1] or 'ASCII') for t in dh ])

def parse_message_ids(references):
    """
    Return a list of message ids, given a header string with message ids

    TODO: comments are not being parsed which means things will break if
    there's a < or > within a comment.
    """
    idx = 0
    ret = []
    idx = string.find(references, '<', idx)

    while idx != -1:
        end = string.find(references, '>', idx)
        ret.append(references[idx+1: end])

        idx = string.find(references, '<', idx + 1)

    return ret

def create_mailtree(path):
    box = mailbox.mbox(path)

    top_messages = MailForest()
    top_messages.fill_tree(box)

    return top_messages
