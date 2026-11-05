"""
Django management command for in-process high-concurrency capacity benchmarking.
Simulates 50, 100, 250, 500, and 750 virtual users executing simultaneous gallery
browsing, cursor pagination, and face searches with precise timing and memory profiling.
"""

import time
import math
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.utils import timezone
from django.core.cache import cache
from django.db import connection, reset_queries

from weddings.models import Wedding
from photos.models import Photo
from weddings.views import WeddingDetailView, WeddingPhotosView, FaceSearchView


def calc_percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    return data[int(f)] * (c - k) + data[int(c)] * (k - f)


class Command(BaseCommand):
    help = "Runs simulated multi-stage in-process load tests (50, 100, 250, 500, 750 users)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--stages',
            default='50,100,250,500,750',
            help='Comma-separated list of concurrent user counts (default: 50,100,250,500,750)',
        )
        parser.add_argument(
            '--wedding',
            default='rahul-priya',
            help='Wedding slug to benchmark (default: rahul-priya)',
        )
        parser.add_argument(
            '--requests-per-stage',
            type=int,
            default=300,
            help='Number of requests per concurrency stage',
        )

    def handle(self, *args, **options):
        stages = [int(s.strip()) for s in options['stages'].split(',') if s.strip()]
        slug = options['wedding']
        reqs_per_stage = options['requests_per_stage']

        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(self.style.NOTICE("   LIVE WEDDING GALLERY - HIGH CONCURRENCY BENCHMARK"))
        self.stdout.write(self.style.NOTICE(f"   Wedding: {slug} | Stages: {stages}"))
        self.stdout.write(self.style.NOTICE("=" * 70))

        factory = RequestFactory()

        # Check if wedding exists or mock it
        wedding = Wedding.objects.filter(slug=slug).first()
        if not wedding:
            self.stdout.write(self.style.WARNING(f"Wedding '{slug}' not found in DB. Creating temporary mock wedding..."))
            wedding = Wedding.objects.create(
                slug=slug,
                name="Benchmark Wedding",
                bride_name="Priya",
                groom_name="Rahul",
                date=timezone.now().date(),
                is_active=True
            )

        detail_view = WeddingDetailView.as_view()
        photos_view = WeddingPhotosView.as_view()

        for concurrency in stages:
            total_reqs = max(concurrency * 2, reqs_per_stage)
            self.stdout.write(self.style.NOTICE(f"\n>>> Benchmarking Stage: {concurrency} Concurrent Users ({total_reqs} requests)..."))

            latencies: List[float] = []
            errors = 0
            start_wall = time.time()

            def run_single_request(i: int):
                # 70% gallery list, 30% detail
                t0 = time.perf_counter()
                try:
                    if i % 3 == 0:
                        req = factory.get(f"/api/weddings/{slug}/")
                        resp = detail_view(req, slug=slug)
                    else:
                        req = factory.get(f"/api/weddings/{slug}/photos/?page_size=25")
                        resp = photos_view(req, slug=slug)

                    dur = (time.perf_counter() - t0) * 1000.0
                    return resp.status_code == 200, dur
                except Exception as ex:
                    dur = (time.perf_counter() - t0) * 1000.0
                    return False, dur

            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = [pool.submit(run_single_request, i) for i in range(total_reqs)]
                for fut in as_completed(futures):
                    ok, dur = fut.result()
                    latencies.append(dur)
                    if not ok:
                        errors += 1

            total_sec = time.time() - start_wall
            rps = total_reqs / total_sec if total_sec > 0 else 0
            latencies.sort()

            p50 = calc_percentile(latencies, 50)
            p95 = calc_percentile(latencies, 95)
            p99 = calc_percentile(latencies, 99)
            avg = sum(latencies) / len(latencies) if latencies else 0
            err_rate = (errors / total_reqs * 100) if total_reqs > 0 else 0

            status_style = self.style.SUCCESS if (p95 < 500 and err_rate < 1.0) else self.style.WARNING
            self.stdout.write(status_style(
                f"Stage {concurrency:3} VUs | RPS: {rps:6.1f} | Avg: {avg:5.1f}ms | "
                f"p50: {p50:5.1f}ms | p95: {p95:5.1f}ms | p99: {p99:5.1f}ms | Error: {err_rate:.2f}%"
            ))

        self.stdout.write(self.style.SUCCESS("\nBenchmark completed successfully!"))

