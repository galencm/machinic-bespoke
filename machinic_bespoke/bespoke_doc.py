# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2018, Galen Curwen-McAdams

import argparse
import os
import multiprocessing
import subprocess
import pathlib
import re
import redis
from fold_ui import keyling

def make_artifact(call_vars):
    artifact_call = "keli src-artifact {source} {field} --filename {filename} --path {path} --db-host {db_host} --db-port {db_port}".format(**call_vars).split()
    if call_vars["verbose"]:
        print("dumping {}".format(call_vars))
    subprocess.call(artifact_call, cwd=call_vars["tmp_path"])
    # write sources and images to csv to run locally?
    # for example: have a repo with images, and if updating text only with no running db

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="input file")
    parser.add_argument("--output", help="output file")
    parser.add_argument("--nop", action="store_true", help="output without any replacements")
    parser.add_argument("--remove-unmatched", action="store_true", help="remove unmatched code blocks that")
    parser.add_argument("--no-pop", action="store_true", help="do not remove source from potential matches after successful match")
    parser.add_argument("--db-host",  default="127.0.0.1", help="db host ip")
    parser.add_argument("--db-port", type=int, default=6379, help="db port")
    parser.add_argument("--db-sources-template",  default="machinic:structured:{host}:{port}", help="db host ip")
    parser.add_argument("--source-field",  default="binary_key", help="field containing image key")
    parser.add_argument("--source-prefix", default="bespokedoc_", help="prefix used for images")
    parser.add_argument("--max-workers", type=int, default=4, help="number of parallel processes to dump images")
    parser.add_argument("--verbose", action="store_true", help="")
    args = parser.parse_args()

    db_settings = {"host" :  args.db_host, "port" : args.db_port}
    redis_conn = redis.StrictRedis(**db_settings, decode_responses=True)

    structured_sources = args.db_sources_template.format(host=args.db_host, port=args.db_port)
    field = args.source_field
    tmp_path =  os.path.join(os.getcwd(), "images")
    # clear existing images?
    if not os.path.isdir(tmp_path):
        if args.verbose:
            print("creating images dir {}".format(tmp_path))
        os.makedirs(tmp_path)

    verbose = args.verbose
    prefix = args.source_prefix
    max_workers = args.max_workers
    calls = []
    files = []
    sources = list(redis_conn.lrange(structured_sources, 0, -1))
    sources_to_dump = []
    used_sources = []
    input_contents = ""

    if args.input:
        with open(args.input, 'r') as f:
          input_contents = f.read()

    # match markdown code blocks annotated as keyling
    keyling_pattern = re.compile(r'(?<=```keyling).*?(?=```)', re.DOTALL)

    for match in re.findall(keyling_pattern, input_contents):
        model = None

        try:
            model = keyling.model(match)
            if args.verbose:
                print(model)
        except Exception as ex:
            if verbose:
                print(ex)
            pass

        if model is not None:
            matched = False
            block_to_replace = "```keyling{}```".format(match)
            for source_key in sources:
                if source_key not in used_sources or args.no_pop is True:
                    source = redis_conn.hgetall(source_key)
                    result = keyling.parse_lines(model, source, source_key, allow_shell_calls=False)
                    if result is not None:
                        image_stanza_template = '![{alt_description}]({image_path} "{description}")'
                        # should add a dedup dict that maps filenames to sources to dump
                        # if using --no-pop
                        sources_to_dump.append(source_key)
                        # filename also created in make_artifact
                        filename = "{}{}.jpg".format(prefix, len(sources_to_dump) - 1)
                        source_replacements = {
                            "alt_description":"",
                            "image_path":"{}/{}".format(os.path.relpath(tmp_path), filename),
                            "description":""
                            }
                        stanza = image_stanza_template.format(**source_replacements)

                        # nop: write output, but do no replacing
                        if not args.nop:
                            input_contents = input_contents.replace(block_to_replace, stanza, 1)

                        if not source_key in used_sources:
                            used_sources.append(source_key)
                        # move to next keyling block after match
                        matched = True
                        break

            if matched is False and args.remove_unmatched is True:
                # only removes keyling using a valid model
                input_contents = input_contents.replace(block_to_replace, "", 1)

    # when no input file is specfied
    # create a basic markdown sequence of all sources
    # and write to file or stdout
    if args.input is None:
        for source_key in sources:
            if source_key not in used_sources:
                source = redis_conn.hgetall(source_key)
                image_stanza_template = '![{alt_description}]({image_path} "{description}")'
                sources_to_dump.append(source_key)
                # filename also created in make_artifact
                filename = "{}{}.jpg".format(prefix, len(sources_to_dump) - 1)
                source_replacements = {
                    "alt_description":"",
                    "image_path":"{}/{}".format(os.path.relpath(tmp_path), filename),
                    "description":""
                    }
                stanza = image_stanza_template.format(**source_replacements)
                input_contents += stanza + "\n"
                # stop after first match see pop/cycle
                used_sources.append(source_key)

    if args.output:
        # write to file if --output is used
        with open(args.output, 'w+') as f:
            f.write(input_contents)
    else:
        # write to stdout
        print(input_contents)

    # get any sources that were included
    # and create images
    for sequence_num, source in enumerate(sources_to_dump):
        # could do additional filtering of sources here
        call_vars = {
        "source" : source,
        "field" : field,
        "sequence_num" : sequence_num,
        "filename" : "{}{}.jpg".format(prefix, sequence_num),
        "data_filename" : "{}{}.csv".format(prefix, sequence_num),
        "path" : tmp_path,
        "db_host" : args.db_host,
        "db_port" : args.db_port,
        "tmp_path" : tmp_path,
        "verbose" : args.verbose
        }
        files.append(call_vars["filename"])
        calls.append(call_vars)

    pool = multiprocessing.Pool(max_workers)
    pool.map(make_artifact, calls)
    pool.close()
    pool.join()
