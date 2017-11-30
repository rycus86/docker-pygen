import unittest

import requests

import pygen
from metrics import MetricsServer


class MetricsTest(unittest.TestCase):
    def tearDown(self):
        MetricsServer.shutdown_current()

    def test_available_metrics(self):
        app = pygen.PyGen(
            template='#',
            restart=['sample-restart'],
            signal=[('sample-signal', 'HUP'), ('sample-interrupt', 'INT')],
            interval=[0]
        )
        app.update_target()
        app.update_target()

        response = requests.get('http://localhost:9413/metrics')
        
        self.assertEqual(response.status_code, 200)
        
        metrics = response.text
        print metrics

        # process / platform
        self.assertIn('python_info{', metrics)
        self.assertIn('process_start_time_seconds ', metrics)

        # app info
        self.assertIn('pygen_app_info{version=', metrics)
        self.assertIn('pygen_app_built_at ', metrics)

        # pygen
        self.assertIn('pygen_generation_seconds_count 2.0', metrics)
        self.assertIn('pygen_generation_seconds_sum ', metrics)

        self.assertIn('pygen_target_update_seconds_count 2.0', metrics)
        self.assertIn('pygen_target_update_seconds_sum ', metrics)

        # pygen signal (actions)
        self.assertIn('pygen_signal_seconds_count 2.0', metrics)
        self.assertIn('pygen_signal_seconds_sum ', metrics)

        self.assertIn('pygen_restart_action_seconds_count{'
                      'target="sample-restart"} 2.0', metrics)
        self.assertIn('pygen_restart_action_seconds_sum{'
                      'target="sample-restart"} ', metrics)

        self.assertIn('pygen_signal_action_seconds_count{'
                      'signal="HUP",target="sample-signal"} 2.0', metrics)
        self.assertIn('pygen_signal_action_seconds_sum{'
                      'signal="HUP",target="sample-signal"} ', metrics)

        self.assertIn('pygen_signal_action_seconds_count{'
                      'signal="INT",target="sample-interrupt"} 2.0', metrics)
        self.assertIn('pygen_signal_action_seconds_sum{'
                      'signal="INT",target="sample-interrupt"} ', metrics)

        # action
        self.assertIn('pygen_action_execution_strategy_seconds_count{'
                      'strategy="local"} 6.0', metrics)
        self.assertIn('pygen_action_execution_strategy_seconds_sum{'
                      'strategy="local"} ', metrics)
        
        # api
        self.assertIn('pygen_api_containers_seconds_count{list_all="0"} ', metrics)
        self.assertIn('pygen_api_containers_seconds_sum{list_all="0"} ', metrics)
        self.assertIn('pygen_api_containers_seconds_bucket{le="0.25",list_all="0"} ', metrics)

        self.assertIn('pygen_api_services_seconds_count{desired_state="running"} ', metrics)
        self.assertIn('pygen_api_services_seconds_sum{desired_state="running"} ', metrics)
        self.assertIn('pygen_api_services_seconds_bucket{desired_state="running",le="0.25"} ', metrics)

        self.assertIn('pygen_api_nodes_seconds_count ', metrics)
        self.assertIn('pygen_api_nodes_seconds_sum ', metrics)
        self.assertIn('pygen_api_nodes_seconds_bucket{le="0.25"} ', metrics)

