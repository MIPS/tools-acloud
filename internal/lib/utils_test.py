#!/usr/bin/env python
#
# Copyright 2016 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for acloud.internal.lib.utils."""

import errno
import getpass
import os
import shutil
import subprocess
import tempfile
import time

import mock

import unittest
from acloud.internal.lib import driver_test_lib
from acloud.internal.lib import utils


class UtilsTest(driver_test_lib.BaseDriverTest):

  def testTempDir_Success(self):
    """Test create a temp dir."""
    self.Patch(os, "chmod")
    self.Patch(tempfile, "mkdtemp", return_value="/tmp/tempdir")
    self.Patch(shutil, "rmtree")
    with utils.TempDir():
      pass
    # Verify.
    tempfile.mkdtemp.assert_called_once()
    shutil.rmtree.assert_called_with("/tmp/tempdir")

  def testTempDir_ExceptionRaised(self):
    """Test create a temp dir and exception is raised within with-clause."""
    self.Patch(os, "chmod")
    self.Patch(tempfile, "mkdtemp", return_value="/tmp/tempdir")
    self.Patch(shutil, "rmtree")

    class ExpectedException(Exception):
      pass

    def _Call():
      with utils.TempDir():
        raise ExpectedException("Expected exception.")
    # Verify. ExpectedException should be raised.
    self.assertRaises(ExpectedException, _Call)
    tempfile.mkdtemp.assert_called_once()
    shutil.rmtree.assert_called_with("/tmp/tempdir")

  def testTempDir_WhenDeleteTempDirNoLongerExist(self):
    """Test create a temp dir and dir no longer exists during deletion."""
    self.Patch(os, "chmod")
    self.Patch(tempfile, "mkdtemp", return_value="/tmp/tempdir")
    expected_error = EnvironmentError()
    expected_error.errno = errno.ENOENT
    self.Patch(shutil, "rmtree", side_effect=expected_error)
    def _Call():
      with utils.TempDir():
        pass
    # Verify no exception should be raised when rmtree raises
    # EnvironmentError with errno.ENOENT, i.e.
    # directory no longer exists.
    _Call()
    tempfile.mkdtemp.assert_called_once()
    shutil.rmtree.assert_called_with("/tmp/tempdir")

  def testTempDir_WhenDeleteEncounterError(self):
    """Test create a temp dir and encoutered error during deletion."""
    self.Patch(os, "chmod")
    self.Patch(tempfile, "mkdtemp", return_value="/tmp/tempdir")
    expected_error = OSError("Expected OS Error")
    self.Patch(shutil, "rmtree", side_effect=expected_error)
    def _Call():
      with utils.TempDir():
        pass

    # Verify OSError should be raised.
    self.assertRaises(OSError, _Call)
    tempfile.mkdtemp.assert_called_once()
    shutil.rmtree.assert_called_with("/tmp/tempdir")

  def testTempDir_OrininalErrorRaised(self):
    """Test original error is raised even if tmp dir deletion failed."""
    self.Patch(os, "chmod")
    self.Patch(tempfile, "mkdtemp", return_value="/tmp/tempdir")
    expected_error = OSError("Expected OS Error")
    self.Patch(shutil, "rmtree", side_effect=expected_error)

    class ExpectedException(Exception):
      pass

    def _Call():
      with utils.TempDir():
        raise ExpectedException("Expected Exception")

    # Verify.
    # ExpectedException should be raised, and OSError
    # should not be raised.
    self.assertRaises(ExpectedException, _Call)
    tempfile.mkdtemp.assert_called_once()
    shutil.rmtree.assert_called_with("/tmp/tempdir")

  def testCreateSshKeyPair_KeyAlreadyExists(self):
    """Test when the key pair already exists."""
    public_key = "/fake/public_key"
    private_key = "/fake/private_key"
    self.Patch(os.path, "exists", side_effect=lambda path: path == public_key)
    self.Patch(subprocess, "check_call")
    utils.CreateSshKeyPairIfNotExist(private_key, public_key)
    self.assertEqual(subprocess.check_call.call_count, 0)

  def testCreateSshKeyPair_KeyAreCreated(self):
    """Test when the key pair created."""
    public_key = "/fake/public_key"
    private_key = "/fake/private_key"
    self.Patch(os.path, "exists", return_value=False)
    self.Patch(subprocess, "check_call")
    self.Patch(os, "rename")
    utils.CreateSshKeyPairIfNotExist(private_key, public_key)
    self.assertEqual(subprocess.check_call.call_count, 1)
    subprocess.check_call.assert_called_with(
        utils.SSH_KEYGEN_CMD + ["-C", getpass.getuser(), "-f", private_key],
        stdout=mock.ANY, stderr=mock.ANY)

  def testRetryOnException(self):
    def _IsValueError(exc):
      return isinstance(exc, ValueError)
    num_retry = 5

    @utils.RetryOnException(_IsValueError, num_retry)
    def _RaiseAndRetry(sentinel):
      sentinel.alert()
      raise ValueError("Fake error.")

    sentinel = mock.MagicMock()
    self.assertRaises(ValueError, _RaiseAndRetry, sentinel)
    self.assertEqual(1 + num_retry, sentinel.alert.call_count)

  def testRetryExceptionType(self):
    """Test RetryExceptionType function."""
    def _RaiseAndRetry(sentinel):
      sentinel.alert()
      raise ValueError("Fake error.")

    num_retry = 5
    sentinel = mock.MagicMock()
    self.assertRaises(ValueError, utils.RetryExceptionType,
                      (KeyError, ValueError), num_retry, _RaiseAndRetry,
                      sentinel=sentinel)
    self.assertEqual(1 + num_retry, sentinel.alert.call_count)

  def testRetry(self):
    """Test Retry."""
    self.Patch(time, "sleep")
    def _RaiseAndRetry(sentinel):
      sentinel.alert()
      raise ValueError("Fake error.")

    num_retry = 5
    sentinel = mock.MagicMock()
    self.assertRaises(ValueError, utils.RetryExceptionType,
                      (ValueError, KeyError), num_retry, _RaiseAndRetry,
                      sleep_multiplier=1,
                      retry_backoff_factor=2,
                      sentinel=sentinel)

    self.assertEqual(1 + num_retry, sentinel.alert.call_count)
    time.sleep.assert_has_calls(
        [mock.call(1), mock.call(2), mock.call(4), mock.call(8), mock.call(16)])


if __name__ == "__main__":
    unittest.main()
