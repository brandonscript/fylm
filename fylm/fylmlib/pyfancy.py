#!/usr/bin/env python

# MIT License

# Copyright (c) 2017 Cosmic Open Source Projects

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Provides methods for manipulating text styling in specific terminals.

Uses a builder pattern to chain outputs, for example, to print "Hello, world!"
in red:

    print pyfancy().red("Hello, world!").get()

Styles can be changed for different text components. Example:

    print pyfancy().red("Hello").raw(", ").blue("world!").get()

No output text is necessary when calling a styling method. This allows
styles to be stacked:

    print pyfancy().red().bold("Hello, world!").get()

There are two provided ways to access the modified text. The first is
direct access to the string object called "out". However, accessing this
object will not reset the style, so any text outputted after will have
the same style as whatever the text was at the end of the chain.

The get() method is better for accessing text because it resets the text
style so no new text will have unwanted styling.

    pyfancy: the main class exported by this module.
"""

class pyfancy:
    def __str__(self): return self.get()
    def __init__(self, parseText="", obj=""):
        # Stores output text, for reset use get()
        self.out = str(obj)
        self.parseText = str(parseText)
        if (self.parseText != ""):
            self.parse(self.parseText)

    codes = { # The different escape codes
        'raw':              0,
        'bold':             1,
        'dim':              2,
        'underlined':       4,
        'blinking':         5,
        'inverted':         7,
        'hidden':           8,
        'black':           30,
        'red':             31,
        'green':           32,
        'yellow':          33,
        'blue':            34,
        'magenta':         35,
        'cyan':            36,
        'light_gray':      37,
        'black_bg':        40,
        'red_bg':          41,
        'green_bg':        42,
        'yellow_bg':       43,
        'blue_bg':         44,
        'purple_bg':       45,
        'cyan_bg':         46,
        'gray_bg':         47,
        'dark_gray':       90,
        'light_red':       91,
        'light_green':     92,
        'light_yellow':    93,
        'light_blue':      94,
        'light_magenta':   95,
        'light_cyan':      96,
        'white':           97,
        'dark_gray_bg':    100,
        'light_red_bg':    101,
        'light_green_bg':  102,
        'light_yellow_bg': 103,
        'light_blue_bg':   104,
        'light_purple_bg': 105,
        'light_cyan_bg':   106,
        'white_bg':        107
    }

    # Stores output text, for reset use get()
    out = ""

    # Returns output text and resets properties
    def get(self):
        return self.out + "\033[0m"

    # Outputs text using print (should work in Python 2 and 3)
    def output(self):
        print(self.get())

    # Adds new text without changing the styling
    def add(self,addition):
        self.out += addition
        return self

    def read(self,file):
        f = open(file, 'r')
        self.out += f.read()
        f.close()
        return self

    def reset(self):
        self.out = ""
        return self

    #Alternate between all the colours of the rainbow
    #No orange, replaced with lightRed
    #No purple/violet so I ignored it
    def rainbow(self,addition=""):
        x = 0
        for i in range(len(addition)):
            if (addition[i] in [" ", "\t", "\n", "\r"]): x+=1
            [self.red, self.light_red, self.yellow, self.green, self.light_blue, self.blue][(i-x) % 6](addition[i])
        return self

    def strip(self):
        text = ""
        i = 0
        while i < len(self.out):
            if self.out[i] == '\033':
                if i + 1 >= len(self.out):
                    return text + '\033'
                if self.out[i + 1] == '[':
                    i += 1
                    if 'm' in self.out[i:]:
                        while self.out[i] != 'm':
                            i += 1
                        i += 1
                    else:
                        text += '\033'
            text += self.out[i]
            i += 1
        return text

    # Simply apply the attribute with the given name
    def attr(self,name):
        if name in self.codes:
            self.out += f"\033[{self.codes[name]}m"

    # Parses text and automatically assigns attributes
    # Attributes are specified through brackets
    # For example, .parse("{red Hello}") is the same as .red("Hello")
    # Multiple attributes can be specified by commas, eg {red,bold Hello}
    # Brackets can be nested, eg {red Hello, {bold world}!}
    # Brackets can be escaped with backslashes
    def parse(self,text):
        i = 0 # Current index
        props = [] # Property stack; required for nested brackets
        while i < len(text):
            c = text[i]
            if c == '\\': # Escape character
                i += 1
                if i < len(text):
                    self.out += text[i]
            elif c == '{': # New property list
                prop = '' # Current property
                i += 1
                curprops = [] # Properties that are part of this bracket
                while text[i] != ' ':
                    if i + 1 == len(text):
                        return self
                    if text[i] == ',':
                        # Properties separated by commas
                        self.attr(prop);
                        curprops.append(prop)
                        prop = ''
                        i += 1
                    prop += text[i]
                    i += 1
                self.attr(prop)
                curprops.append(prop)
                # Add properties to property stack
                props.append(curprops)
            elif c == '}':
                # Reset styling
                self.raw()
                # Remove last entry from property stack
                if len(props) >= 1:
                    props.pop()
                # Apply all properties from any surrounding brackets
                for plist in props:
                    for p in plist:
                        self.attr(p)
            else:
                self.out += c
            i += 1
        return self


    # Multicolored text
    def multi(self,string):
        i = 31 # ID of escape code; starts at 31 (red) and goes to 36 (cyan)
        for c in string: # Iterate through string
            self.out += "\033[" + str(i) + "m" + c
            i += 1 # Why u no have ++i? >:(
            if(i > 36): i = 31
        return self

# Adds a formatting function to pyfancy with the specified name and formatting code
# This shouldn't be exported
def _add(name,number):
    def inner(self, addition = ""):
        self.out += f"\033[{number}m{addition}"
        return self
    setattr(pyfancy,name,inner)

# Generate all default color / format codes
for item in pyfancy.codes.items():
    if len(item) > 1: # Just in case
        _add(item[0],item[1])
