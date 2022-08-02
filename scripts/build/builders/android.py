# Copyright (c) 2021 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shlex
from enum import Enum, auto

from .builder import Builder


class AndroidBoard(Enum):
    ARM = auto()
    ARM64 = auto()
    X64 = auto()
    X86 = auto()
    AndroidStudio_ARM = auto()
    AndroidStudio_ARM64 = auto()
    AndroidStudio_X64 = auto()
    AndroidStudio_X86 = auto()

    def TargetCpuName(self):
        if self in [AndroidBoard.ARM, AndroidBoard.AndroidStudio_ARM]:
            return 'arm'
        elif self in [AndroidBoard.ARM64, AndroidBoard.AndroidStudio_ARM64]:
            return 'arm64'
        elif self in [AndroidBoard.X64, AndroidBoard.AndroidStudio_X64]:
            return 'x64'
        elif self in [AndroidBoard.X86, AndroidBoard.AndroidStudio_X86]:
            return 'x86'
        else:
            raise Exception('Unknown board type: %r' % self)

    def AbiName(self):
        if self.TargetCpuName() == 'arm':
            return 'armeabi-v7a'
        elif self.TargetCpuName() == 'arm64':
            return 'arm64-v8a'
        elif self.TargetCpuName() == 'x64':
            return 'x86_64'
        elif self.TargetCpuName() == 'x86':
            return 'x86'
        else:
            raise Exception('Unknown board type: %r' % self)

    def IsIde(self):
        return self in [
            AndroidBoard.AndroidStudio_ARM,
            AndroidBoard.AndroidStudio_ARM64,
            AndroidBoard.AndroidStudio_X64,
            AndroidBoard.AndroidStudio_X86,
        ]


class AndroidApp(Enum):
    CHIP_TOOL = auto()
    CHIP_TEST = auto()
    CHIP_TVServer = auto()
    CHIP_TV_CASTING_APP = auto()

    def AppName(self):
        if self == AndroidApp.CHIP_TOOL:
            return "CHIPTool"
        elif self == AndroidApp.CHIP_TEST:
            return "CHIPTest"
        elif self == AndroidApp.CHIP_TVServer:
            return "CHIPTVServer"
        elif self == AndroidApp.CHIP_TV_CASTING_APP:
            return "CHIPTVCastingApp"
        else:
            raise Exception('Unknown app type: %r' % self)

    def AppGnArgs(self):
        gn_args = {}
        if self in [AndroidApp.CHIP_TVServer, AndroidApp.CHIP_TV_CASTING_APP]:
            gn_args['chip_config_network_layer_ble'] = False
        return gn_args

    def ExampleName(self):
        if self == AndroidApp.CHIP_TVServer:
            return "tv-app"
        elif self == AndroidApp.CHIP_TV_CASTING_APP:
            return "tv-casting-app"
        else:
            return None

    def Modules(self):
        if self == AndroidApp.CHIP_TVServer:
            return ["platform-app", "content-app"]
        else:
            return None


class AndroidBuilder(Builder):

    def __init__(self, root, runner, board: AndroidBoard, app: AndroidApp):
        super(AndroidBuilder, self).__init__(root, runner)
        self.board = board
        self.app = app

    def validate_build_environment(self):
        for k in ['ANDROID_NDK_HOME', 'ANDROID_HOME']:
            if k not in os.environ:
                raise Exception(f'Environment {k} missing, cannot build android libraries')

        # SDK manager must be runnable to 'accept licenses'
        sdk_manager = os.path.join(os.environ['ANDROID_HOME'], 'tools', 'bin',
                                   'sdkmanager')

        # New SDK manager at cmdline-tools/latest/bin/
        new_sdk_manager = os.path.join(os.environ['ANDROID_HOME'], 'cmdline-tools', 'latest',
                                       'bin', 'sdkmanager')
        if (not (os.path.isfile(sdk_manager) and os.access(sdk_manager, os.X_OK)) and
                not (os.path.isfile(new_sdk_manager) and os.access(new_sdk_manager, os.X_OK))):
            raise Exception("'%s' and '%s' is not executable by the current user" %
                            (sdk_manager, new_sdk_manager))

        # In order to accept a license, the licenses folder is updated with the hash of the
        # accepted license
        android_home = os.environ['ANDROID_HOME']
        licenses = os.path.join(android_home, 'licenses')
        if not os.path.exists(licenses):
            # Initial install may not have licenses at all
            if not os.access(android_home, os.W_OK):
                raise Exception(
                    "'%s' is NOT writable by the current user (needed to create licenses folder for accept)"
                    % android_home)

        elif not os.access(licenses, os.W_OK):
            raise Exception(
                "'%s' is NOT writable by the current user (needed to accept licenses)"
                % licenses)

    def copyToSrcAndroid(self):
        # JNILibs will be copied as long as they reside in src/main/jniLibs/ABI:
        #    https://developer.android.com/studio/projects/gradle-external-native-builds#jniLibs
        # to avoid redefined in IDE mode, copy to another place and add that path in build.gradle

        # We do NOT use python builtins for copy, so that the 'execution commands' are available
        # when using dry run.
        jnilibs_dir = os.path.join(
            self.root, 'src/android/', self.app.AppName(), 'app/libs/jniLibs', self.board.AbiName())
        libs_dir = os.path.join(
            self.root, 'src/android/', self.app.AppName(), 'app/libs')
        self._Execute(
            ['mkdir', '-p', jnilibs_dir],
            title=f'Prepare Native libs {self.identifier}',
        )


        # TODO: Runtime dependencies should be computed by the build system rather than hardcoded
        # GN supports getting these dependencies like:
        #   gn desc out/android-x64-chip_tool/ //src/controller/java runtime_deps
        #   gn desc out/android-x64-chip_tool/ //src/setup_payload/java runtime_deps
        # However  this assumes that the output folder has been populated, which will not be
        # the case for `dry-run` executions. Hence this harcoding here.
        #
        #   If we unify the JNI libraries, libc++_shared.so may not be needed anymore, which could
        # be another path of resolving this inconsistency.
        for libName in ['libSetupPayloadParser.so', 'libCHIPController.so', 'libc++_shared.so']:
            self._Execute(['cp', os.path.join(self.output_dir, 'lib', 'jni', self.board.AbiName(
            ), libName), os.path.join(jnilibs_dir, libName)])

        jars = {
            'CHIPController.jar': 'src/controller/java/CHIPController.jar',
            'SetupPayloadParser.jar': 'src/setup_payload/java/SetupPayloadParser.jar',
            'AndroidPlatform.jar': 'src/platform/android/AndroidPlatform.jar',
        }

        for jarName in jars:
            self._Execute(['cp', os.path.join(
                self.output_dir, 'lib', jars[jarName]), os.path.join(libs_dir, jarName)])

    def copyToExampleAndroid(self):
        jnilibs_dir = os.path.join(
            self.root, 'examples', self.app.ExampleName(), 'android/App/app/libs/jniLibs', self.board.AbiName())
        libs_dir = os.path.join(
            self.root, 'examples', self.app.ExampleName(), 'android/App/app/libs')
        self._Execute(
            ['mkdir', '-p', jnilibs_dir],
            title=f'Prepare Native libs {self.identifier}',
        )


        if self.app.ExampleName() == 'tv-casting-app':
            libs = ['libc++_shared.so', 'libTvCastingApp.so']
        else:
            libs = ['libSetupPayloadParser.so',
                    'libc++_shared.so', 'libTvApp.so']
        for libName in libs:
            self._Execute(['cp', os.path.join(self.output_dir, 'lib', 'jni', self.board.AbiName(
            ), libName), os.path.join(jnilibs_dir, libName)])

        if self.app.ExampleName() == 'tv-casting-app':
            jars = {
                'AndroidPlatform.jar': 'third_party/connectedhomeip/src/platform/android/AndroidPlatform.jar',
                'CHIPAppServer.jar': 'third_party/connectedhomeip/src/app/server/java/CHIPAppServer.jar',
                'TvCastingApp.jar': 'TvCastingApp.jar',
            }
        else:
            jars = {
                'SetupPayloadParser.jar': 'third_party/connectedhomeip/src/setup_payload/java/SetupPayloadParser.jar',
                'AndroidPlatform.jar': 'third_party/connectedhomeip/src/platform/android/AndroidPlatform.jar',
                'CHIPAppServer.jar': 'third_party/connectedhomeip/src/app/server/java/CHIPAppServer.jar',
                'TvApp.jar': 'TvApp.jar',
            }
        for jarName in jars:
            self._Execute(['cp', os.path.join(
                self.output_dir, 'lib', jars[jarName]), os.path.join(libs_dir, jarName)])

    def gradlewBuildSrcAndroid(self):
        # App compilation
        self._Execute(
            [
                f'{self.root}/src/android/{self.app.AppName()}/gradlew',
                '-p',
                f'{self.root}/src/android/{self.app.AppName()}',
                f'-PmatterBuildSrcDir={self.output_dir}',
                '-PmatterSdkSourceBuild=false',
                f'-PbuildDir={self.output_dir}',
                'assembleDebug',
            ],
            title=f'Building APP {self.identifier}',
        )

    def gradlewBuildExampleAndroid(self):
        # Example compilation
        if self.app.Modules():
            for module in self.app.Modules():
                self._Execute(
                    [
                        f'{self.root}/examples/{self.app.ExampleName()}/android/App/gradlew',
                        '-p',
                        f'{self.root}/examples/{self.app.ExampleName()}/android/App/',
                        f'-PmatterBuildSrcDir={self.output_dir}',
                        '-PmatterSdkSourceBuild=false',
                        f'-PbuildDir={self.output_dir}/{module}',
                        f':{module}:assembleDebug',
                    ],
                    title=f'Building Example {self.identifier}, module {module}',
                )

        else:
            self._Execute(
                [
                    f'{self.root}/examples/{self.app.ExampleName()}/android/App/gradlew',
                    '-p',
                    f'{self.root}/examples/{self.app.ExampleName()}/android/App/',
                    f'-PmatterBuildSrcDir={self.output_dir}',
                    '-PmatterSdkSourceBuild=false',
                    f'-PbuildDir={self.output_dir}',
                    'assembleDebug',
                ],
                title=f'Building Example {self.identifier}',
            )

    def generate(self):
        self._Execute([
            'python3', 'third_party/android_deps/set_up_android_deps.py'
        ], title='Setting up Android deps through Gradle')

        if not os.path.exists(self.output_dir):
            # NRF does a in-place update  of SDK tools
            if not self._runner.dry_run:
                self.validate_build_environment()

            gn_args = {'target_os': 'android', 'target_cpu': self.board.TargetCpuName()}
            gn_args['android_ndk_root'] = os.environ['ANDROID_NDK_HOME']
            gn_args['android_sdk_root'] = os.environ['ANDROID_HOME']
            gn_args |= self.app.AppGnArgs()

            args_str = ""
            for key, value in gn_args.items():
                if type(value) == bool:
                    args_str += f'{key}=true ' if value else f'{key}=false '
                else:
                    args_str += '%s="%s" ' % (key, shlex.quote(value))
            args = f'--args={args_str}'

            gn_gen = [
                'gn', 'gen', '--check', '--fail-on-unused-args', self.output_dir, args,
            ]

            exampleName = self.app.ExampleName()
            if exampleName is not None:
                gn_gen += [f'--root={self.root}/examples/{exampleName}/android/']

            if self.board.IsIde():
                gn_gen += ['--ide=json',
                           '--json-ide-script=//scripts/examples/gn_to_cmakelists.py']

            self._Execute(gn_gen, title=f'Generating {self.identifier}')

            new_sdk_manager = os.path.join(os.environ['ANDROID_HOME'], 'cmdline-tools', 'latest',
                                           'bin', 'sdkmanager')
            if (os.path.isfile(new_sdk_manager) and os.access(new_sdk_manager, os.X_OK)):
                self._Execute(
                    [
                        'bash',
                        '-c',
                        f'yes | {new_sdk_manager} --licenses >/dev/null',
                    ],
                    title='Accepting NDK licenses @ cmdline-tools',
                )

            else:
                sdk_manager = os.path.join(os.environ['ANDROID_HOME'], 'tools', 'bin',
                                           'sdkmanager')
                self._Execute(
                    ['bash', '-c', f'yes | {sdk_manager} --licenses >/dev/null'],
                    title='Accepting NDK licenses @ tools',
                )

    def _build(self):
        if self.board.IsIde():
            # App compilation IDE
            # TODO: Android Gradle with module and -PbuildDir= will caused issue, remove -PbuildDir=
            self._Execute(
                [
                    f'{self.root}/src/android/{self.app.AppName()}/gradlew',
                    '-p',
                    f'{self.root}/src/android/{self.app.AppName()}',
                    f'-PmatterBuildSrcDir={self.output_dir}',
                    '-PmatterSdkSourceBuild=true',
                    f'-PmatterSourceBuildAbiFilters={self.board.AbiName()}',
                    'assembleDebug',
                ],
                title=f'Building APP {self.identifier}',
            )

        else:
            self._Execute(
                ['ninja', '-C', self.output_dir],
                title=f'Building JNI {self.identifier}',
            )


            exampleName = self.app.ExampleName()
            if exampleName is None:
                self.copyToSrcAndroid()
                self.gradlewBuildSrcAndroid()
            else:
                self.copyToExampleAndroid()
                self.gradlewBuildExampleAndroid()

    def build_outputs(self):
        if self.board.IsIde():
            return {
                f'{self.app.AppName()}-debug.apk': os.path.join(
                    self.root,
                    "src/android",
                    self.app.AppName(),
                    'app/build/outputs/apk/debug/app-debug.apk',
                )
            }

        elif self.app.ExampleName() is not None:
            return {
                f'{self.app.AppName()}app-debug.apk': os.path.join(
                    self.output_dir, 'outputs', 'apk', 'debug', 'app-debug.apk'
                )
            }

        else:
            return {
                f'{self.app.AppName()}app-debug.apk': os.path.join(
                    self.output_dir, 'outputs', 'apk', 'debug', 'app-debug.apk'
                ),
                'CHIPController.jar': os.path.join(
                    self.output_dir,
                    'lib',
                    'src/controller/java/CHIPController.jar',
                ),
                'AndroidPlatform.jar': os.path.join(
                    self.output_dir,
                    'lib',
                    'src/platform/android/AndroidPlatform.jar',
                ),
                'SetupPayloadParser.jar': os.path.join(
                    self.output_dir,
                    'lib',
                    'src/setup_payload/java/SetupPayloadParser.jar',
                ),
                f'jni/{self.board.AbiName()}/libSetupPayloadParser.so': os.path.join(
                    self.output_dir,
                    'lib',
                    'jni',
                    self.board.AbiName(),
                    'libSetupPayloadParser.so',
                ),
                f'jni/{self.board.AbiName()}/libCHIPController.so': os.path.join(
                    self.output_dir,
                    'lib',
                    'jni',
                    self.board.AbiName(),
                    'libCHIPController.so',
                ),
                f'jni/{self.board.AbiName()}/libc++_shared.so': os.path.join(
                    self.output_dir,
                    'lib',
                    'jni',
                    self.board.AbiName(),
                    'libc++_shared.so',
                ),
            }
