import attr
from collections import deque
import re
import sys
import textwrap
import configparser


TASK_RE = re.compile(r'(\t*)- +(.*?)$')
PROJECT_RE = re.compile(r'.+:$')
INDENT = 2

@attr.s
class Task:
    desc = attr.ib()
    level = attr.ib()
    parent = attr.ib()
    children = attr.ib(default=attr.Factory(list))
    tags = attr.ib(default=attr.Factory(dict))
    root = attr.ib(default=False)

@attr.s
class TagDef:
    tag = attr.ib()
    name = attr.ib()
    has_val = attr.ib()
    default = attr.ib()


def extract(line):
    tags = {}

    for tagdef in TAGS:
        value = None
        match = None

        if tagdef.has_val:
            match = re.search(rf'@{tagdef.tag}\(([^)]*)\)\s*', line)
        else:
            match = re.search(rf'@{tagdef.tag}\s*', line)

        if match:
            if tagdef.has_val:
                value = match.group(1)
            span = match.span(0)
            line = line[0:span[0]] + line[span[1]:]
            tags[tagdef.name] = value

    return line, tags


def output_task(task):
    def indent(lvl):
        return ' ' * INDENT * lvl

    out = f'\ntask "{task.desc}" {{\n'

    if task.parent and 'allocate' in task.parent.tags:
        if 'allocate' in task.tags:
            out += f'  purge allocate\n'

    for tag, val in task.tags.items():
        if not val:
            val = ''
        out += f'  {tag} {val}\n'


    out = out.rstrip()

    out = textwrap.indent(out, indent(task.level))

    if not task.root:
        print(out)

    for child in task.children:
        output_task(child)

    if not task.root:
        print(indent(task.level) + '}')


root = Task("", -1, parent=None, root=True)

def proc(fn):
    parent = root
    pstk = [parent]
    last_level = 0
    with open(fn) as f:
        for line in f:
            line = line.rstrip()
            # Makes project look like top level tasks
            if PROJECT_RE.match(line):
                line = f'- {line[0:-1]}'
            match = TASK_RE.match(line)
            if match:
                level = len(match.group(1))
                desc, tags = extract(match.group(2))

                if level > last_level:
                    pstk.append(parent)
                    parent = parent.children[-1]
                else:
                    for _ in range(parent.level - level + 1):
                        parent = pstk.pop()
                last_level = level
                task = Task(desc=desc.strip(), level=level, parent=parent, tags=tags)
                parent.children.append(task)

    output_task(root)

if __name__ == '__main__':
    #print(extract('test @dog(5) blah', 'dog', int))

    config = configparser.RawConfigParser()
    config.read('tp2tj.cfg')

    global TAGS
    TAGS = []
    for section in config.sections():
        if section.startswith('@'):
            tag = section[1:]
            name = config.get(section, 'name')
            has_val = config.getboolean(section, 'has_value')
            if has_val and config.has_option(section, 'default'):
                default = config.get(section, 'default')
            else:
                default = None
            TAGS.append(TagDef(tag, name, has_val, default))

    proc(sys.argv[1])
