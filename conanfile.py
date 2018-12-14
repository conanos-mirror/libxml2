#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
import os
from conans import ConanFile, tools, AutoToolsBuildEnvironment
from conanos.build import config_scheme
import shutil

class Libxml2Conan(ConanFile):
    name = "libxml2"
    version = "2.9.8"
    url = "https://github.com/bincrafters/conan-libxml2"
    description = "libxml2 is a software library for parsing XML documents"
    homepage = "https://xmlsoft.org"
    license = "MIT"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = 'shared=True', 'fPIC=True'
    requires = "zlib/1.2.11@conanos/stable", "libiconv/1.15@conanos/stable"
    exports = ["LICENSE.md"]
    exports_sources = ["FindLibXml2.cmake"]
    _source_subfolder = "source_subfolder"

    @property
    def _is_msvc(self):
        return self.settings.compiler == 'Visual Studio'



    def source(self):
        tools.get("http://xmlsoft.org/sources/libxml2-{0}.tar.gz".format(self.version))
        os.rename("libxml2-{0}".format(self.version), self._source_subfolder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        del self.settings.compiler.libcxx
		
        config_scheme(self)


    def build(self):
        if self._is_msvc:
            self._build_windows()
        else:
            self._build_with_configure()

    def _build_windows(self):

        with tools.chdir(os.path.join(self._source_subfolder, 'win32')):
            vcvars = tools.vcvars_command(self.settings)
            debug = "yes" if self.settings.build_type == "Debug" else "no"
            static = "no" if self.options.shared else "yes"

            includes = ";".join(self.deps_cpp_info["libiconv"].include_paths +
                                self.deps_cpp_info["zlib"].include_paths)
            libs = ";".join(self.deps_cpp_info["libiconv"].lib_paths +
                            self.deps_cpp_info["zlib"].lib_paths)
            configure_command = "%s && cscript configure.js " \
                "zlib=1 compiler=msvc prefix=%s cruntime=/%s debug=%s static=%s include=\"%s\" lib=\"%s\"" % (
                        vcvars,
                        self.package_folder,
                        self.settings.compiler.runtime,
                        debug,
                        static,
                        includes,
                        libs)
            self.output.info(configure_command)
            self.run(configure_command)

            # Fix library names because they can be not just zlib.lib
            libname = self.deps_cpp_info['zlib'].libs[0]
            if not libname.endswith('.lib'):
                libname += '.lib'
            tools.replace_in_file("Makefile.msvc",
                                  "LIBS = $(LIBS) zlib.lib",
                                  "LIBS = $(LIBS) %s" % libname)
            libname = self.deps_cpp_info['libiconv'].libs[0]
            if not libname.endswith('.lib'):
                libname += '.lib'
            tools.replace_in_file("Makefile.msvc",
                                  "LIBS = $(LIBS) iconv.lib",
                                  "LIBS = $(LIBS) %s" % libname)

            self.run("%s && nmake /f Makefile.msvc install" % vcvars)

    def _build_with_configure(self):
        in_win = self.settings.os == "Windows"
        env_build = AutoToolsBuildEnvironment(self, win_bash=in_win)
        if not in_win:
            env_build.fpic = self.options.fPIC
        full_install_subfolder = tools.unix_path(self.package_folder)
        with tools.environment_append(env_build.vars):
            with tools.chdir(self._source_subfolder):
                # fix rpath
                if self.settings.os == "Macos":
                    tools.replace_in_file("configure", r"-install_name \$rpath/", "-install_name ")
                configure_args = ['--with-python=no', '--without-lzma', '--prefix=%s' % full_install_subfolder]
                if env_build.fpic:
                    configure_args.extend(['--with-pic'])
                if self.options.shared:
                    configure_args.extend(['--enable-shared', '--disable-static'])
                else:
                    configure_args.extend(['--enable-static', '--disable-shared'])

                # Disable --build when building for iPhoneSimulator. The configure script halts on
                # not knowing if it should cross-compile.
                build = None
                if self.settings.os == "iOS" and self.settings.arch == "x86_64":
                    build = False
                    
                env_build.configure(args=configure_args, build=build)
                env_build.make(args=["install"])

    def package(self):
        self.copy("FindLibXml2.cmake", ".", ".")
        # copy package license
        self.copy("COPYING", src=self._source_subfolder, dst="licenses", ignore_case=True, keep_path=False)
        if self.settings.os == "Windows":
            # There is no way to avoid building the tests, but at least we don't want them in the package
            for prefix in ["run", "test"]:
                for test in glob.glob("%s/bin/%s*" % (self.package_folder, prefix)):
                    os.remove(test)
        for header in ["win32config.h", "wsockcompat.h"]:
            self.copy(pattern=header, src=os.path.join(self._source_subfolder, "include"),
                      dst=os.path.join("include", "libxml2"), keep_path=False)
        if self._is_msvc:
            # remove redundant libraries to avoid confusion
            os.unlink(os.path.join(self.package_folder, 'lib', 'libxml2_a_dll.lib'))
            os.unlink(os.path.join(self.package_folder, 'lib',
                                   'libxml2_a.lib' if self.options.shared else 'libxml2.lib'))
        
        if self.settings.os == "Windows":
            tools.mkdir(os.path.join(self.package_folder,"lib","pkgconfig"))
            shutil.copyfile(os.path.join(self.build_folder,self._source_subfolder,"libxml-2.0.pc.in"),
                            os.path.join(self.package_folder,"lib","pkgconfig", "libxml-2.0.pc"))
            replacements_pc = {
                "@prefix@"            :  self.package_folder,
                "@exec_prefix@"       :  "${prefix}/bin",
                "@libdir@"            :  "${prefix}/lib",
                "@includedir@"        :  "${prefix}/include",
                "@WITH_MODULES@"      :  "",
                "@VERSION@"           :  self.version,
                "@ICU_LIBS@"          :  "",
                "@THREAD_LIBS@"       :  "",
                "@Z_LIBS@"            :  "",
                "@LZMA_LIBS@"         :  "",
                "@ICONV_LIBS@"        :  "-liconv",
                "@M_LIBS@"            :  "",
                "@WIN32_EXTRA_LIBADD@":  "",
                "@LIBS@"              :  "",
                "@XML_INCLUDEDIR@"    :  "-I"+os.path.join(self.package_folder,"include","libxml2"),
                "@XML_CFLAGS@"        :  "",
            }
            for s, r in replacements_pc.items():
                tools.replace_in_file(os.path.join(self.package_folder,"lib","pkgconfig", "libxml-2.0.pc"),s,r)

    def package_info(self):
        if self._is_msvc:
            self.cpp_info.libs = ['libxml2' if self.options.shared else 'libxml2_a']
        else:
            self.cpp_info.libs = ['xml2']
        self.cpp_info.includedirs = ["include/libxml2"]
        if not self.options.shared:
            self.cpp_info.defines = ["LIBXML_STATIC"]
        if self.settings.os == "Linux" or self.settings.os == "Macos":
            self.cpp_info.libs.append('m')
        if self.settings.os == "Windows":
            self.cpp_info.libs.append('ws2_32')
