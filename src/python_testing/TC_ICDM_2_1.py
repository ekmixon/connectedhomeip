#
#    Copyright (c) 2023 Project CHIP Authors
#    All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
import chip.clusters as Clusters
from matter_testing_support import MatterBaseTest, async_test_body, default_matter_test_main
from mobly import asserts


class TC_ICDM_2_1(MatterBaseTest):
    async def read_icdm_attribute_expect_success(self, endpoint, attribute):
        cluster = Clusters.Objects.IcdManagement
        return await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attribute)

    @async_test_body
    async def test_TC_ICDM_2_1(self):

        endpoint = self.user_params.get("endpoint", 0)

        self.print_step(1, "Commissioning, already done")
        attributes = Clusters.IcdManagement.Attributes
        idleModeInterval = 0

        # Idle Mode Interval attribute test
        if (self.check_pics("ICDM.S.A0000")):
            self.print_step(2, "Read IdleModeInterval Attribute")

            idleModeInterval = await self.read_icdm_attribute_expect_success(endpoint=endpoint,
                                                                             attribute=attributes.IdleModeInterval)
            asserts.assert_greater_equal(idleModeInterval, 1, "IdleModeInterval attribute is smaller than minimum value (1).")
            asserts.assert_less_equal(idleModeInterval, 64800, "IdleModeInterval attribute is greater than maximum value (64800).")
        else:
            asserts.assert_true(False, "IdleModeInterval is a mandatory attribute and must be present in the PICS file")

        # Active Mode Interval attribute test
        if (self.check_pics("ICDM.S.A0001")):
            self.print_step(2, "Read ActiveModeInterval Attribute")

            idleModeInterval *= 1000  # Convert seconds to milliseconds
            activeModeInterval = await self.read_icdm_attribute_expect_success(endpoint=endpoint,
                                                                               attribute=attributes.ActiveModeInterval)
            asserts.assert_greater_equal(activeModeInterval, 300,
                                         "ActiveModeInterval attribute is smaller than minimum value (300).")
            asserts.assert_less_equal(activeModeInterval, idleModeInterval,
                                      "ActiveModeInterval attribute is greater than the IdleModeInterval attrbiute.")
        else:
            asserts.assert_true(False, "ActiveModeInterval is a mandatory attribute and must be present in the PICS file")

        # Active Mode Threshold attribute test
        if (self.check_pics("ICDM.S.A0002")):
            self.print_step(2, "Read ActiveModeThreshold Attribute")

            activeModeThreshold = await self.read_icdm_attribute_expect_success(endpoint=endpoint,
                                                                                attribute=attributes.ActiveModeThreshold)
            asserts.assert_greater_equal(activeModeThreshold, 300,
                                         "ActiveModeThreshold attribute is smaller than minimum value (300).")
        else:
            asserts.assert_true(False, "ActiveModeThreshold is a mandatory attribute and must be present in the PICS file")

        # RegisteredClients attribute test
        if (self.check_pics("ICDM.S.A0003")):
            self.print_step(2, "Read RegisteredClients Attribute")

            await self.read_icdm_attribute_expect_success(endpoint=endpoint,
                                                          attribute=attributes.RegisteredClients)

        # ICDCounter attribute test
        if (self.check_pics("ICDM.S.A0003")):
            self.print_step(2, "Read ICDCounter Attribute")

            await self.read_icdm_attribute_expect_success(endpoint=endpoint,
                                                          attribute=attributes.ICDCounter)

        # ClientsSupportedPerFabric attribute test
        if (self.check_pics("ICDM.S.A0003")):
            self.print_step(2, "Read ClientsSupportedPerFabric Attribute")

            clientsSupportedPerFabric = await self.read_icdm_attribute_expect_success(endpoint=endpoint,
                                                                                      attribute=attributes.ClientsSupportedPerFabric)
            asserts.assert_greater_equal(clientsSupportedPerFabric, 1,
                                         "ActiveModeThreshold attribute is smaller than minimum value (300).")


if __name__ == "__main__":
    default_matter_test_main()
