from uuid import uuid4
import re
import matplotlib.pyplot as plt
import argparse

# Note that GOTO within loops can behave unexpectedly
import sys

fig = plt.figure()

class Plotter:

    def __init__(self, datum = (0.0,0.0,0.0)):
        self.data = []
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.set_datum(datum)

    def execute(self, x = 0.0, y = 0.0, z = 0.0):
        # execute a movement
        self.x = x
        self.y = y
        self.z = z

        vector = (x, y, z)

        self.data.append(vector)

    # Absolute coordinates.
    def x_abs(self, x):
        return x + self.x_datum

    def y_abs(self, y):
        return y + self.y_datum

    def z_abs(self, z):
        return z + self.z_datum

    def set_datum(self, datum):
        self.x_datum, self.y_datum, self.z_datum = datum
        self.datum = datum
        locations['datum'] = datum
        self.data.insert(0, datum)

    def plot(self):

        # only plot those values which are on on below the z_datum
        x_data = []
        y_data = []

        on_surface = True
        ax = fig.add_subplot(111, aspect='equal')

        i = 0

        while i < len(self.data) - 1:
            i += 1
            x,y,z = self.data[i]

            #print '%d,%d,%d' % (x,y,z)

            ax.scatter(x, y)

            if self.z_abs(z) <= self.z_datum:
                x_data.append(self.x_abs(x))
                y_data.append(self.y_abs(y))

            else:
                # plot last set of data as scatter and start new set
                # create new subplot
                ax.plot(x_data, y_data)
                x_data = []
                y_data = []

        ax.plot(x_data, y_data)

    def show(self):
        self.plot()
        plt.show()


class Program:
    raw = ''
    codeblocks = {'start': []}
    execution_order = ['start']
    line_map = {} # line_number: (label, index)
    stop_execute = False
    current_line = 1
    line_count = 0

    # block tag opening patterns
    while_pattern = re.compile(r'WHILE (?P<condition>(\w|.|\s)+) DO')
    if_pattern = re.compile(r'IF (?P<var>\w+)\s?(?P<operator>(=|>|<|!)+)\s?(?P<val>\d+) (?P<end>(THEN|GOTO \d+))')
    for_pattern = re.compile(r'FOR (?P<index>\w+)\s?=\s?(?P<start_value>\d+) (TO|to) (?P<end_value>\w+)( STEP (?P<increment>\d+))?')
    do_until_pattern = r''

    end_pattern = re.compile(r'END')

    def __init__(self, interface, code):
        # code without any indentation
        self.raw = '\n'.join(re.sub(r'^(\s+|(;.+))', '', l) for l in code.replace('\n\n', '\n').split('\n')).replace('\n\n', '\n')

        # code with indentation preserved
        self.human_raw = code

        # minified code, keeping inline comments but removing all else

        self.interface = interface

        self.reprocess()

    def is_block(self, l):
        if self.while_pattern.match(l) or self.for_pattern.match(l) or self.if_pattern.match(l):
            return True
        else:
            return False

    def generate_block(self, lines, i):
        """
        Recursively generates a CodeBlock with CodeLine/CodeBlock objects in the lines param
        Returns a tuple of (CodeBlock, end_line)
        """

        l = lines[i]

        # Double check that this is a block
        if self.is_block(l):
            cb = CodeBlock(self, l)

            # for handling inline GOTO commands
            if self.if_pattern.match(l):
                m = self.if_pattern.match(l)
                end = m.group('end')
                if not 'THEN' in end:
                    return cb, i


            # iterate every line, if another level of code is found, recursively run self and add the returned CodeBlock to current CodeBlock lines param
            while not self.end_pattern.match(l):
                i += 1
                l = lines[i]

                if self.is_block(l):
                    cb_embedded, i = self.generate_block(lines, i)
                    cb.lines.append(cb_embedded)
                else:
                    if not self.end_pattern.match(l):
                        cb.lines.append(CodeLine(self, l))

            return cb, i
        else:
            return CodeLine(self, l), i

    def reprocess(self):
        split_raw = self.raw.split('\n')

        i = 0

        current_label = 'start'

        while i < len(split_raw):
            l = split_raw[i]

            # grabs the label if it exists
            line_pattern = re.compile(r'^(?P<label>\d+)?\s*(?P<code>.+)')
            line_match = line_pattern.match(l)

            if line_match:
                code = line_match.group('code')
                label = line_match.group('label')

                # remove label from line
                split_raw[i] = code

                if label:
                    # generate codeblock
                    if label in self.codeblocks:
                        print 'Cannot execute program. Label %s used twice!' % str(label)
                        return
                    current_label = label
                    self.codeblocks[current_label] = []
                    self.execution_order.append(current_label)
                else:
                    label = 'all'

            else:
                print 'Error identifying line structure, trying to run anyway. %s' % l
                label = 'all'
                code = l
                split_raw[i] = code # might fix it

            cb, i = self.generate_block(split_raw, i)
            self.codeblocks[current_label].append(cb)
            self.line_map[i+1] = (current_label,len(self.codeblocks[current_label])-1)

            i += 1

        self.line_count = i

    def goto(self, l):
        print '> GOTO %s' % l
        x = None
        for n, (label, _) in self.line_map.iteritems():
            if label == l:
                x = n
                break
        if x:
            self.stop_execute = True
            self.current_line = x
            self.stop_execute = False
            self.execute()
        else:
            print "label doesn't exist!"

    def execute_line(self, n):

        try:
            label, index = self.line_map[n]
            self.codeblocks[label][index].execute()
        except KeyError:
            pass

    def execute(self):
        while not self.stop_execute and self.current_line <= self.line_count:
            self.execute_line(self.current_line)
            self.current_line += 1

class CodeLine:

    def __init__(self, program, line):
        self.program = program
        self.line = line

    def execute(self):
        if "GOTO" in self.line:
            goto, n = self.line.split(' ')
            self.program.goto(n)
            return
        print '> %s' % self.line
        process_line(self.program.interface, self.line)


class CodeBlock:
    # Recursively self generating class to handle logic code

    def __init__(self, program, logic):
        self.program = program
        self.logic = logic
        self.lines = []

    def execute_all_lines(self):
        for l in self.lines:
            l.execute()

    def execute(self):
        if self.program.while_pattern.match(self.logic):
            self.execute_all_lines()
        elif self.program.for_pattern.match(self.logic):
            m = self.program.for_pattern.match(self.logic)
            index = m.group('index')
            start_value = int(m.group('start_value'))
            end_value = int(m.group('end_value'))
            increment = m.group('increment')
            if increment:
                increment = int(increment)

            vars[index] = start_value - 1

            while vars[index] != end_value:
                vars[index] += 1
                self.execute_all_lines()
        elif self.program.if_pattern.match(self.logic):
            m = self.program.if_pattern.match(self.logic)
            var = m.group('var')
            operator = m.group('operator')
            val = int(m.group('val'))
            end = m.group('end')

            # TODO check that this is correct syntax for ==
            if operator == '=':
                if vars[var] == val:
                    if 'THEN' in end:
                        self.execute_all_lines()
                    else:
                        goto, n = end.split(' ')
                        self.program.goto(n)
            elif operator == '<':
                if vars[var] < val:
                    if 'THEN' in end:
                        self.execute_all_lines()
                    else:
                        goto, n = end.split(' ')
                        self.program.goto(n)
            elif operator == '>':
                if vars[var] > val:
                    if 'THEN' in end:
                        self.execute_all_lines()
                    else:
                        goto, n = end.split(' ')
                        self.program.goto(n)
            elif operator == '<=':
                if vars[var] <= val:
                    if 'THEN' in end:
                        self.execute_all_lines()
                    else:
                        goto, n = end.split(' ')
                        self.program.goto(n)
            elif operator == '>=':
                if vars[var] >= val:
                    if 'THEN' in end:
                        self.execute_all_lines()
                    else:
                        goto, n = end.split(' ')
                        self.program.goto(n)
            elif operator == '!=':
                if vars[var] != val:
                    if 'THEN' in end:
                        self.execute_all_lines()
                    else:
                        goto, n = end.split(' ')
                        self.program.goto(n)


def MOVE(interface, args):
    move_pattern = re.compile(r"(?P<val>.+)")
    m = move_pattern.match(args)

    if not m:
        print "Incorrect syntax"
        return

    val = m.group('val')

    x, y, z = get_cords_from_input(val)

    interface.execute(x, y, z)



def APPRO(interface, args):
    appro_pattern = re.compile(r"(?P<val>.+),\s?(?P<offset>\d+)")
    m = appro_pattern.match(args)

    if not m:
        print 'Incorrect syntax'
        return

    x,y,z = get_cords_from_input(m.group('val'))
    offset = float(m.group('offset'))

    interface.execute(x,y,z+offset)


def DEPART(interface, args):
    appro_pattern = re.compile(r"(?P<offset>\d+)")
    m = appro_pattern.match(args)

    if not m:
        print 'Incorrect syntax'
        return

    offset = float(m.group('offset'))

    interface.execute(interface.x,interface.y,interface.z+offset)



def SET(interface, args):

    set_pattern = re.compile(r"(?P<var>\w+)\s?=\s?(?P<val>(\w|\s|.)+)")

    m = set_pattern.match(args)

    if not m:
        print "Incorrect syntax"
        return

    var = m.group('var')
    val = m.group('val')

    locations[var] = get_cords_from_input(val)


def get_cords_from_input(input):
    input_parts = input.split(':')

    trans_pattern = re.compile(r"TRANS\s?\((?P<dx>-?(\d|\.)+),\s?(?P<dy>-?(\d|\.)+),\s?(?P<dz>-?(\d|\.)+)\)")
    shift_pattern = re.compile(r"SHIFT\s?\((?P<knownpoint>\w+)\s(BY|by)\s(?P<dx>-?(\d|\.)+),\s?(?P<dy>-?(\d|\.)+),\s?(?P<dz>-?(\d|\.)+)\)")

    current_x, current_y, current_z = (0,0,0)

    for part in input_parts:
        trans_match = trans_pattern.match(part)
        shift_match = shift_pattern.match(part)

        if trans_match:
            # trans has different orientation so need to flip x axis.. (TODO and z? - doing this anyway seeing as not worried for now)
            x, y, z = (trans_match.group('dx'), trans_match.group('dy'), trans_match.group('dz'))
            current_x += -float(x)
            current_y += float(y)
            current_z += -float(z)
        elif shift_match:
            knownpoint = shift_match.group('knownpoint')
            dx = float(shift_match.group('dx'))
            dy = float(shift_match.group('dy'))
            dz = float(shift_match.group('dz'))

            if knownpoint not in locations:
                print 'Existing location %s does not exist!' % part
                return 0,0,0

            x,y,z = locations[knownpoint]
            current_x += dx + x
            current_y += dy + y
            current_z += dz + z
        else:
            if part not in locations:
                print 'Existing location %s does not exist!' % part
                return 0,0,0

            #assume is a variable name
            x, y, z = locations[part]
            current_x += x
            current_y += y
            current_z += z

    return current_x, current_y, current_z


def EXECUTE(interface, args):
    """
    executes a program. TODO Need to check proper usage for this
    Currently just running a specified file with commands in
    """
    try:
        with open(args) as f:
            p = Program(interface, f.read())
            p.execute()
    except IOError:
        print "file does not exist!"

def _debug(interface, args):
    import pdb
    pdb.set_trace()

def process_line(interface, cmd):
    # if using python 3.0, could use cmd, *args = cmd.split(' '), I think.
    cmd_parts = cmd.split(' ')
    cmd_string = cmd_parts[0]

    if cmd_string in funcs:
        func = funcs[cmd_string]
        func(interface, cmd.replace(cmd_string + ' ', ''))

    elif cmd_string == 'SHOW':
        interface.show()
    elif cmd_string == 'QUIT' or cmd_string == 'quit' or cmd_string == 'q' or cmd_string == 'exit':
        quit()
    elif re.match(r'(?P<var>\w+)\s?=\s?(?P<val>.+)', cmd):
        m = re.match(r'(?P<var>\w+)\s?=\s?(?P<val>.+)', cmd)
        if len(m.group('var')) > 15:
            print 'Variables names must be no longer than 15 characters'
        else:
            vars[m.group('var').replace(' ', '')] = get_var(m.group('val'))
    elif cmd_string in locations:
        print locations[cmd_string]
    elif cmd_string in vars:
        print vars[cmd_string]
    else:
        print "Unknown function %s!" % cmd_string

def IGNORE(interface, args):
    pass

def get_var(l):
    """
    Gets a variable out of vars dictionary
    Also processes any mathematical modifications
    """
    negative_pattern = re.compile(r'^-.+')
    addition_pattern = re.compile(r'(?P<n1>.+)\s?\+\s?(?P<n2>.+)')

    addition_match = addition_pattern.match(l)

    if addition_match:
        n1 = addition_match.group('n1').replace(' ', '')
        n2 = addition_match.group('n2').replace(' ', '')

        if n1 in vars:
            n1 = vars[n1]

        if n2 in vars:
            n2 = vars[n2]

        try:
            return float(n1) + float(n2)
        except:
            print 'Error processing maths %s. Possible that it references an unassigned variable' % l
            return 0

    elif l in vars:
        return vars[l]
    else:
        try:
            return float(l)
        except:
            print 'Error processing variable %s' % str(l)
            return 0


# live funcs
funcs = {
    "MOVE": MOVE,
    "MOVES": MOVE,
    "APPRO": APPRO,
    "APPROS": APPRO,
    "DEPART": DEPART,
    "DEPARTS": DEPART,
    "SET": SET,
    "EXECUTE": EXECUTE,
    "debug": _debug,
    }

# functions to ignore
funcs.update({
    "CLOSEI": IGNORE,
    "OPENI": IGNORE,
    "SIGNAL": IGNORE,
    "DELAY": IGNORE,
    ".PROGRAM": IGNORE,
    ".END": IGNORE,
    "WAIT": IGNORE,
    })
vars = {}
locations = {}

if __name__ == '__main__':
    cmd = ''

    plot = Plotter((0,0,0))

    if len(sys.argv[1:]) == 3:
        code_file, output, intial_cmd = sys.argv[1:]
        process_line(plot, intial_cmd)
        process_line(plot, 'EXECUTE %s' % code_file)
        plot.plot()
        plt.savefig(output)
    else:
        while True:
            cmd = raw_input("CMD: ")

            process_line(plot, cmd)