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
    def pruned_trees(self):
        trees = {}
        for k in self.keys():
            if self[k].message_id == k:
                trees[k] = self[k]

        return trees

    def fill_tree(self, box):
        for m in box:
            msg_id = m.get('Message-id')
            msg_id = parse_message_ids(msg_id)[0]

            references = parse_message_ids(m.get('References', ''))
            references.extend(parse_message_ids(m.get('In-Reply-To', '')))

            if len(references) > 0:
                if references[0] not in self:
                    self[references[0]] = MailTree(references[0])

                tree_key = self[references[0]].message_id
                for ref in references:
                    if ref not in self:
                        self[ref] = self[references[0]]

                if msg_id not in self:
                    self[msg_id] = self[references[0]]
                    self[tree_key].addChild(m, references)
                elif msg_id == self[msg_id].message_id:
                    self[msg_id].hydrate(m, references)
                    self[tree_key].graft(self[msg_id])
                else:
                    self[tree_key].addChild(m, references)

            else:
                if msg_id in self:
                    self[msg_id].hydrate(m)
                else:
                    self[msg_id] = MailTree(msg_id, m)

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
