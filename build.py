#!/usr/bin/env python

import platform
import os
import re
from cpt.packager import ConanMultiPackager
from conanos.sdk.profile import filter

__NAME__ = 'libxml2'

if platform.system() == 'Windows':
    os.environ['CONAN_VISUAL_VERSIONS'] = os.environ.get('CONAN_VISUAL_VERSIONS','15')

os.environ['CONAN_USERNAME'] = os.environ.get('CONAN_USERNAME','conanos')

if __name__ == "__main__":    
    PATTERN = re.compile(r'conanio/(?P<compiler>gcc|clang)(?P<version>\d+)(-(?P<arch>\w+))?')
    m = PATTERN.match(os.environ.get('CONAN_DOCKER_IMAGE',''))
    docker_entry_script = ''
    if m and os.path.exists('docker_entry_script.sh'):
        compiler = m.group('compiler')
        version  = m.group('version')
        arch     = 'x86_64' if not m.group('arch') else m.group('arch')
        docker_entry_script ='/bin/bash docker_entry_script.sh %s %s %s'%(compiler,version,arch)
        CONANOS_SDK=os.environ.get("CONANOS_SDK")
        if CONANOS_SDK:
            docker_entry_script += " && export CONANOS_SDK=%s"%CONANOS_SDK
    
        
    builder = ConanMultiPackager(docker_entry_script=docker_entry_script)
    builder.add_common_builds(pure_c=True)

    filter(__NAME__,builder)
    
    builder.run()
