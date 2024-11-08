import argparse
import asyncio
from datetime import datetime
import aiofiles

from _conf import COMMON_SUBDOMAINS, BRUTEFORCE_FILE, BRUTEFORCE_LEVEL, BRUTEFORCE_OUTPUT_FOLDER, BRUTEFORCE_OUTPUT_FORMAT
from _log import scan_log
from _utils import async_load_targets
from domain import resolve_domain
from domain.subdomain_dns_scanner import collect_subdomains

_module_name = "domain.subdomain"


async def _load_subdomains_from_file(file_path):
    subdomains = []
    async with aiofiles.open(file_path, mode='r') as f:
        async for line in f:
            subdomain = line.strip()
            if subdomain and not subdomain.startswith('#'):
                subdomains.append(subdomain)
    scan_log.info_status_result(_module_name, "LOADED", f"{len(subdomains)} subdomains from '{file_path}'")
    return subdomains


async def resolve_ips_from_subdomains(domains, level=BRUTEFORCE_LEVEL, brute_force_file=BRUTEFORCE_FILE, output_folder=BRUTEFORCE_OUTPUT_FOLDER, output_format=BRUTEFORCE_OUTPUT_FORMAT):
    found_ips = set()  # To store unique IP addresses
    scan_log.info_status_result(_module_name, "STARTED", "The search for subdomains has begun")
    async def search_subdomains(current_domain, current_level, output_file):
        if current_level > 0:
            subdomains = collect_subdomains(current_domain) + [f"{sub}.{current_domain}" for sub in COMMON_SUBDOMAINS]
        else:
            subdomains = [current_domain]

        if brute_force_file and current_level > 0:
            additional_subdomains = await _load_subdomains_from_file(brute_force_file)
            subdomains.extend([f"{sub}.{current_domain}" for sub in additional_subdomains])


        subdomains = list(filter(None, set(subdomains)))
        resolved_ips = []

        try:
            resolved_ips = await asyncio.gather(*[resolve_domain(sub) for sub in subdomains])
        except Exception as e:
            scan_log.error_status_result(_module_name, "ERROR", f"Failed resolve_domain!\n{e}")

        resolved_ips = list(filter(None, resolved_ips))
        for ip in resolved_ips:
            found_ips.add(ip)

        if resolved_ips:
            # Recording results to a file as they are received
            if output_file:
                if output_format == 'domain-ip':
                    await output_file.write(f"{current_domain} - {', '.join(resolved_ips)}\n")
                elif output_format == 'ip':
                    await output_file.write(f"{', '.join(resolved_ips)}\n")

        if current_level < level:
            tasks = [search_subdomains(sub, current_level + 1, output_file) for sub in subdomains]
            await asyncio.gather(*tasks)

    # Opening a file for writing
    output_file_path = f"{output_folder}domain.subdomain results {datetime.now()}.txt" if output_folder else None
    output_file = await aiofiles.open(output_file_path, mode='w') if output_file_path else None

    # Processing of each domain
    for domain in domains:
        try:
            await search_subdomains(domain, 0, output_file)
        except Exception as e:
            scan_log.error_status_result(_module_name, "ERROR", f"Failed resolve_ips_from_subdomains for '{domain}'\n{e}")

    # Closing a file if it has been opened
    if output_file:
        await output_file.close()
        scan_log.info_status_result(_module_name, "COMPLETE", f"Results saved to '{output_file_path}' file")

    return list(found_ips)  # Return found IP addresses


async def _load_domains_from_file(file_path):
    async with aiofiles.open(file_path, mode='r') as f:
        content = await f.read()
        domains = [domain.strip() for domain in content.split(',') if domain.strip()]
    scan_log.info_status_result(_module_name, "LOADED", f"{len(domains)} domains from '{file_path}'")
    return domains


def main(remaining_args):
    parser = argparse.ArgumentParser(description="Subdomain resolution module")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-ds', '--domains', help="Comma-separated list of domains (no spaces)")
    group.add_argument('-iF', '--input-file', help="Path to a file with comma-separated domains")

    parser.add_argument('-dBL', '--level', type=int, default=BRUTEFORCE_LEVEL,
                        help="Level of subdomain brute-forcing (default: BRUTEFORCE_LEVEL)")
    parser.add_argument('-dBF', '--brute-force-file', default=BRUTEFORCE_FILE,
                        help="Path to brute-force subdomains file (default: BRUTEFORCE_FILE)")
    parser.add_argument('-oF', '--output-folder', default=BRUTEFORCE_OUTPUT_FOLDER,
                        help="Output folder for results")
    parser.add_argument('-oFmt', '--output-format', choices=['domain-ip', 'ip'], default='domain-ip',
                        help="Output format: 'domain-ip' or 'ip' (default: 'domain-ip')")
    args = parser.parse_args(remaining_args)

    domains = []
    if args.domains:
        domains = [domain.strip() for domain in args.domains.split(',')]
    elif args.input_file:
        _, domains = asyncio.run(async_load_targets(args.input_file))

    domains = list(filter(None, set(domains)))

    # Running asynchronous search for all domains
    asyncio.run(resolve_ips_from_subdomains(domains, args.level, args.brute_force_file, args.output_folder, args.output_format))
