# mroute_monitor
Soemthing to log into switches and show the multicast routing table

Logs into a list of cisco routers (with a tacacs username/password), runs ```show int desc``` and ```show ip mroute``` and displays the output on a simple webpage, you can see groups, the source (for S,G entries), incoming and outgoing interfaces on each router, how long it's been in the table, and the various flags

