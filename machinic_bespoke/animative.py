# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2018, Galen Curwen-McAdams

import argparse
import multiprocessing
import subprocess
import os
import redis

# create an animated gif from images
# sequenced with fold-ui
# by accessing the list of sequenced sources
# that use machinic light key structure
# and using gifsicle to create an animated gif


def make_artifact(call_vars):
    artifact_call = "keli src-artifact {source} {field} --filename {filename} --path {path} --db-host {db_host} --db-port {db_port}".format(
        **call_vars
    ).split()
    subprocess.call(artifact_call, cwd=call_vars["tmp_path"])
    filename_gif = "{}.gif".format(call_vars["filename"])
    subprocess.call(
        ["convert", call_vars["filename"], filename_gif], cwd=call_vars["tmp_path"]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="animation filename")
    parser.add_argument("--db-host", default="127.0.0.1", help="db host ip")
    parser.add_argument("--db-port", type=int, default=6379, help="db port")
    parser.add_argument(
        "--db-sources-template",
        default="machinic:structured:{host}:{port}",
        help="db host ip",
    )
    parser.add_argument(
        "--source-field", default="binary_key", help="field containing image key"
    )
    parser.add_argument(
        "--animate-frame-start",
        type=int,
        default=0,
        help="starting item (used in list slice of sources)",
    )
    parser.add_argument(
        "--animate-frame-end",
        type=int,
        default=-1,
        help="starting item (used in list slice of sources)",
    )
    parser.add_argument(
        "--animate-delay", type=int, default=200, help="animation delay(100 = 1 second)"
    )
    parser.add_argument("--animate-resize", default=None, help="gifsicle resize string")
    parser.add_argument(
        "--animate-frames-prefix",
        default="animative",
        help="prefix used for temporary frames",
    )
    parser.add_argument("--verbose", action="store_true", help="")
    args = parser.parse_args()

    db_settings = {"host": args.db_host, "port": args.db_port}
    redis_conn = redis.StrictRedis(**db_settings, decode_responses=True)

    structured_sources = args.db_sources_template.format(
        host=args.db_host, port=args.db_port
    )
    field = args.source_field
    tmp_path = "/tmp"
    prefix = args.animate_frames_prefix
    files = []
    anim_delay = args.animate_delay
    if not args.filename.endswith(".gif"):
        args.filename += ".gif"
    # put file where script is run
    output_file = os.path.join(os.getcwd(), args.filename)
    pool = multiprocessing.Pool(4)
    calls = []
    for sequence_num, source in enumerate(
        list(redis_conn.lrange(structured_sources, 0, -1))[
            args.animate_frame_start : args.animate_frame_end
        ]
    ):
        # could do additional filtering of sources here
        call_vars = {
            "source": source,
            "field": field,
            "sequence_num": sequence_num,
            "filename": "{}_{}.jpg".format(prefix, sequence_num),
            "path": tmp_path,
            "db_host": args.db_host,
            "db_port": args.db_port,
            "tmp_path": tmp_path,
        }
        # could be sped up by running artifact calls in parallel
        filename_gif = "{}.gif".format(call_vars["filename"])
        # duplicated in make_artifact function
        files.append(filename_gif)
        calls.append(call_vars)

    # create images from db in parallel
    pool.map(make_artifact, calls)
    pool.close()
    pool.join()

    subprocess.call(
        ["gifsicle", "-d{}".format(anim_delay), *files, "-o", output_file], cwd=tmp_path
    )
    if args.animate_resize:
        subprocess.call(["gifsicle", "--batch", "--resize", args.resize, output_file])
