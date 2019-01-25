from mwparserfromhell import parse
from mwparserfromhell.nodes import *
from mwparserfromhell.nodes.external_link import ExternalLink
from mwparserfromhell.nodes.wikilink import Wikilink
from mwparserfromhell.nodes.comment import Comment
from anytree import Node, RenderTree


def title_text(parent):
    if not parent.title:
        return ''
    title = ''
    for t1 in parent.title.nodes:
        title = pretty_text(t1) + ' '
    return title.strip()


def contents_text(parent):
    if not parent.contents:
        return ''
    title = ''
    for t1 in parent.contents.nodes:
        title = pretty_text(t1) + ' '
    return title.strip()


def pretty_text(thing):
    txt = ''
    if isinstance(thing, Text):
        txt = str(thing)
    elif isinstance(thing, ExternalLink):
        txt = title_text(thing)
    elif isinstance(thing, Wikilink):
        txt = title_text(thing)
    elif isinstance(thing, Tag):
        txt = contents_text(thing)
    elif isinstance(thing, Template) or isinstance(thing, Comment):
        txt = ''
        # ignore for now
    elif isinstance(thing, Heading):
        txt = (title_text(thing) + ": ")
    else:
        print('what is this thing {}'.format(type(thing)))
    return txt.strip()


if __name__ == "__main__":
    """
    Wiki source here: https://hemonc.org/wiki/Main_Page
    """
    last_nodes = dict()
    nodes = list()
    chemotherapy_nodes = list()
    is_chemotherapy = False
    with open('./cancer_wiki/dlbcl.txt') as f:
        wikicode = parse(f.read())
        cur_level = 0
        cur_title = None
        cur_node = None
        for n in wikicode.nodes:
            if isinstance(n, Heading):
                cur_title = title_text(n)

                is_chemotherapy = (cur_title == 'Chemotherapy')

                if cur_level == 0:
                    if is_chemotherapy:
                        cur_node = Node(cur_title, drugs=list(), brands=list(), instructions=list())
                    else:
                        cur_node = Node(cur_title, data=list())

                else:
                    parent_level = n.level - 1
                    if parent_level in last_nodes:
                        if is_chemotherapy:
                            cur_node = Node(cur_title, parent=last_nodes[parent_level], drugs=list(), brands=list(),
                                            instructions=list())
                        else:
                            cur_node = Node(cur_title, parent=last_nodes[parent_level], data=list(), brands=list())
                    else:
                        if is_chemotherapy:
                            cur_node = Node(cur_title, drugs=list(), instructions=list())
                        else:
                            cur_node = Node(cur_title, data=list())

                cur_level = n.level
                last_nodes[cur_level] = cur_node
                nodes.append(cur_node)

                if is_chemotherapy:
                    chemotherapy_nodes.append(cur_node)

                # print(cur_title, cur_level)
            else:
                if cur_level > 0:
                    text = pretty_text(n)
                    if len(text) > 0:
                        if is_chemotherapy:
                            if isinstance(n, Wikilink):
                                spl = text.split('(')
                                drug = spl[0].strip()
                                cur_node.drugs.append(drug)
                                if len(spl) == 1:
                                    cur_node.brands.append(drug)
                                else:
                                    cur_node.brands.append(spl[1].split(')')[0].strip())
                            else:
                                # cur_node.instructions.append(text)
                                pass
                        else:
                            if len(cur_node.data) > 0:
                                cur_node.data[-1] = (cur_node.data[-1] + ' ' + text).strip()
                            else:
                                cur_node.data.append(text)
                    else:
                        if is_chemotherapy:
                            pass
                        elif len(cur_node.data) > 0:
                            # don't just keep adding empty ones
                            if cur_node.data[-1] != '':
                                cur_node.data.append('')
                        else:
                            cur_node.data.append('')

    for cn in chemotherapy_nodes:
        print('--------------------------')
        print(RenderTree(cn))

    print('--------------------------')