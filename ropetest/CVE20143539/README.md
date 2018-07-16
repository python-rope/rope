== List of files ==

project/			- directory containing an example python module
CVE-2014-3539.py	- python script which tries to load an example python module
				      for re-factoring (normal workflow simulation)
generate_payload.py - generates payload.txt (evil code to run)
payload.txt			- example payload (running /bin/uptime)
run_reproducer.sh	- main file that sticks above together

== Usage ==

Run ./run_reproducer.sh.
If the system is vulnerable, you'll see the output similar to below:

  $ ./run_reproducer.sh
  SUCCESS:  15:13:46 up 21:26, 2 users,  load average: 0.02, 0.63, 1.01

