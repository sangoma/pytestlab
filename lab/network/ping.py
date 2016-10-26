import plumbum


# More recent versions iputils merged the two ping commands. Attempt to
# support both the older and newer versions
try:
    ping_cmds = {4: plumbum.local['ping'],
                 6: plumbum.local['ping6']}
except plumbum.CommandNotFound:
    ping_cmds = {4: plumbum.local['ping']['-4'],
                 6: plumbum.local['ping']['-6']}
