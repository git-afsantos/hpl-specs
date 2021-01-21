# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Exceptions
###############################################################################

class HplSanityError(Exception):
    pass


class HplTypeError(Exception):
    @classmethod
    def ros_field(cls, rostype, field, expr):
        return cls("ROS '{}' has no field '{}': {}".format(
            rostype, field, expr))

    @classmethod
    def ros_array(cls, rostype, expr):
        return cls("ROS '{}' is not an array: {}".format(
            rostype, expr))

    @classmethod
    def ros_index(cls, rostype, idx, expr):
        return cls("ROS '{}' index {} out of range: {}".format(
            rostype, idx, expr))

    @classmethod
    def already_defined(cls, topic, ot, nt):
        return cls("Topic '{}' cannot be both of type {} and type {}".format(
            topic, ot, nt))

    @classmethod
    def undefined(cls, topic):
        return cls("Unknown type for topic '{}'".format(topic))


class HplSyntaxError(Exception):
    @classmethod
    def duplicate_metadata(cls, key, pid=None):
        which = ""
        if pid is not None:
            which = " for property '{}'".format(pid)
        return cls("duplicate metadata key '{}'{}".format(key, which))

    @classmethod
    def from_lark(cls, lark_exception):
        return cls(str(lark_exception))
