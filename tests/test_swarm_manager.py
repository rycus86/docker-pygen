import unittest

import actions
import pygen
import swarm_worker

from utils import EnhancedDict


class SwarmManagerTest(unittest.TestCase):
    def setUp(self):
        # TODO remove this
        from utils import set_log_level; set_log_level('DEBUG')

        self.manager = pygen.PyGen(template='#', interval=[0], swarm_manager=True,
                                   workers=['localhost'])
        self.worker = swarm_worker.Worker('localhost')
        self.worker.start()

        self.assertIsNotNone(self.manager.swarm_manager)

        self.to_restore = dict()

    def tearDown(self):
        self.worker.shutdown()
        self.manager.stop()

        for (target, name), original in self.to_restore.items():
            setattr(target, name, original)

    def patch(self, target, name, replacement):
        original = getattr(target, name)
        self.to_restore[(target, name)] = original
        setattr(target, name, replacement)

    def test_signal(self):
        self.manager.signal_targets = [('signal-target', 'HUP')]
        
        captured_matchers = list()
        captured_signals = list()

        def patched_kill(signal):
            captured_signals.append(signal)

        def patched_match(action, name):
            self.assertEqual(action.api, self.worker.api)

            captured_matchers.append(name)
            container = EnhancedDict(name=name, raw=EnhancedDict(kill=patched_kill))
            return [container]

        self.patch(actions.SignalAction, 'matching_containers', patched_match)
            
        self.manager.update_target()

        self.assertEqual(captured_matchers, ['signal-target'])
        self.assertEqual(captured_signals, ['HUP'])

    def test_restart(self):
        self.manager.restart_targets = ['restart-target']
        
        captured_matchers = list()
        captured_restarts = list()

        def patched_restart(name):
            captured_restarts.append(name)

        def patched_match(action, name):
            self.assertEqual(action.api, self.worker.api)

            captured_matchers.append(name)
            container = EnhancedDict(name=name, raw=EnhancedDict(restart=lambda: patched_restart(name)))
            return [container]

        self.patch(actions.RestartAction, 'matching_containers', patched_match)

        self.manager.update_target()

        self.assertEqual(captured_matchers, ['restart-target'])
        self.assertEqual(captured_restarts, ['restart-target'])
 
