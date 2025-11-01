#!/usr/bin/env bash

cmake -B build-docker \ 
  -DCMAKE_BUILD_TYPE=Debug \
  -G Ninja \
  -DENABLE_LARGE_TESTS=ON

cmake --build build-docker -j20
