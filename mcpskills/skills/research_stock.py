#!/opt/anaconda3/envs/mcpskills/bin/python3
"""
Stock Research Orchestrator

Coordinates comprehensive stock research workflow across multiple phases.

Usage:
    ./skills/research_stock.py INTC
    ./skills/research_stock.py INTC --phases technical
    ./skills/research_stock.py INTC --phases technical,fundamental
    ./skills/research_stock.py INTC --skip-cleanup

Output:
    - Creates work/{SYMBOL}_{YYYYMMDD}/ directory with research outputs
    - Deletes older directories for same symbol by default
    - Tracks completed phases in metadata file
"""

import os
import sys
import argparse
import json
import subprocess
import glob
import shutil
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Import company overview function for early execution
sys.path.insert(0, os.path.dirname(__file__))
from research_fundamental import save_company_overview

# Constants
WORK_DIR = 'work'

# Define required API keys for each phase
PHASE_API_KEYS = {
    'technical': ['OPENBB_PAT'],
    'fundamental': ['OPENBB_PAT'],
    'research': ['PERPLEXITY_API_KEY'],
    'analysis': ['PERPLEXITY_API_KEY'],
    'sec': ['SEC_FIRM', 'SEC_USER'],  # SEC requires company name and email
    'wikipedia': [],  # No API key needed
    'report': [],  # No API key needed
    'deep': ['ANTHROPIC_API_KEY'],
    'final': []  # No API key needed
}


def validate_api_keys(phases_to_run):
    """
    Validate that required API keys are present for the phases to run.

    Args:
        phases_to_run: List of phase names

    Returns:
        tuple: (success: bool, missing_keys: list)
    """
    missing_keys = set()

    for phase in phases_to_run:
        required_keys = PHASE_API_KEYS.get(phase, [])
        for key in required_keys:
            if not os.getenv(key):
                missing_keys.add(key)

    return len(missing_keys) == 0, sorted(missing_keys)


def validate_ticker(symbol):
    """
    Validate ticker symbol using lookup_ticker.py.

    Args:
        symbol: Ticker symbol to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Use lookup_ticker to search for the symbol
        result = subprocess.run(
            [os.path.join(os.path.dirname(__file__), 'lookup_ticker.py'), symbol, '--limit', '1'],
            capture_output=True,
            text=True,
            timeout=30
        )

        # If lookup_ticker found results, ticker is valid
        if result.returncode == 0 and 'SUCCESS' in result.stdout:
            return True
        else:
            return False
    except Exception as e:
        print(f"Warning: Could not validate ticker: {e}")
        # If validation fails, continue anyway (might be network issue)
        return True


def create_work_directory(symbol):
    """
    Create work directory for research outputs.

    Args:
        symbol: Stock ticker symbol

    Returns:
        str: Path to work directory
    """
    date_str = datetime.now().strftime('%Y%m%d')
    work_dir = os.path.join(WORK_DIR, f"{symbol}_{date_str}")

    # Create main work directory
    os.makedirs(work_dir, exist_ok=True)

    print(f"✓ Created work directory: {work_dir}")
    return work_dir


def cleanup_old_directories(symbol, current_dir, skip_cleanup=False):
    """
    Delete older work directories for the same symbol.

    Args:
        symbol: Stock ticker symbol
        current_dir: Current work directory to preserve
        skip_cleanup: If True, skip cleanup
    """
    if skip_cleanup:
        print(f"⊘ Skipping cleanup (--skip-cleanup flag set)")
        return

    # Find all work directories for this symbol
    pattern = os.path.join(WORK_DIR, f"{symbol}_*")
    matching_dirs = glob.glob(pattern)

    deleted_count = 0
    for dir_path in matching_dirs:
        # Don't delete current directory
        if dir_path != current_dir:
            try:
                shutil.rmtree(dir_path)
                deleted_count += 1
                print(f"✓ Deleted old directory: {dir_path}")
            except Exception as e:
                print(f"Warning: Could not delete {dir_path}: {e}")

    if deleted_count == 0:
        print(f"✓ No old directories to clean up")
    else:
        print(f"✓ Cleaned up {deleted_count} old director{'y' if deleted_count == 1 else 'ies'}")


def create_metadata(work_dir, symbol):
    """
    Create metadata file to track research progress.

    Args:
        work_dir: Work directory path
        symbol: Stock ticker symbol

    Returns:
        dict: Metadata dictionary
    """
    metadata = {
        'symbol': symbol,
        'research_date': datetime.now().strftime('%Y-%m-%d'),
        'research_timestamp': datetime.now().isoformat(),
        'phases_completed': [],
        'phases_failed': [],
        'errors': [],
        'data_sources': {}
    }

    # Save metadata
    metadata_path = os.path.join(work_dir, '00_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Created metadata file: {metadata_path}")
    return metadata


def save_metadata(work_dir, metadata):
    """
    Save updated metadata to file.

    Args:
        work_dir: Work directory path
        metadata: Metadata dictionary to save
    """
    metadata_path = os.path.join(work_dir, '00_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def run_phase(phase_name, phase_script, symbol, work_dir, metadata, metadata_lock=None, extra_args=None):
    """
    Execute a research phase script.

    Args:
        phase_name: Name of the phase (e.g., 'technical')
        phase_script: Path to phase script
        symbol: Stock ticker symbol
        work_dir: Work directory path
        metadata: Metadata dictionary
        metadata_lock: Threading lock for metadata updates (optional)
        extra_args: List of extra command-line arguments (optional)

    Returns:
        bool: True if phase succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Phase: {phase_name.upper()}")
    print(f"{'='*60}")

    try:
        # Build command with optional extra args
        cmd = [phase_script, symbol, '--work-dir', work_dir]
        if extra_args:
            cmd.extend(extra_args)

        # Execute phase script with appropriate timeout
        # Deep research needs more time due to extended thinking and MCP tools
        phase_timeout = 1800 if phase_name == 'deep' else 300  # 30 min for deep, 5 min for others

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=phase_timeout
        )

        # Print script output
        if result.stdout:
            print(result.stdout)

        # Thread-safe metadata update
        if metadata_lock:
            with metadata_lock:
                if result.returncode == 0:
                    metadata['phases_completed'].append(phase_name)
                    print(f"\n✓ Phase '{phase_name}' completed successfully")
                    save_metadata(work_dir, metadata)
                    return True
                else:
                    error_msg = f"Phase '{phase_name}' failed with return code {result.returncode}"
                    if result.stderr:
                        error_msg += f": {result.stderr}"
                    metadata['phases_failed'].append(phase_name)
                    metadata['errors'].append(error_msg)
                    print(f"\n❌ {error_msg}")
                    save_metadata(work_dir, metadata)
                    return False
        else:
            # Non-parallel execution (backward compatible)
            if result.returncode == 0:
                metadata['phases_completed'].append(phase_name)
                print(f"\n✓ Phase '{phase_name}' completed successfully")
                save_metadata(work_dir, metadata)
                return True
            else:
                error_msg = f"Phase '{phase_name}' failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                metadata['phases_failed'].append(phase_name)
                metadata['errors'].append(error_msg)
                print(f"\n❌ {error_msg}")
                save_metadata(work_dir, metadata)
                return False

    except subprocess.TimeoutExpired:
        timeout_minutes = phase_timeout // 60
        error_msg = f"Phase '{phase_name}' timed out after {timeout_minutes} minutes"
        if metadata_lock:
            with metadata_lock:
                metadata['phases_failed'].append(phase_name)
                metadata['errors'].append(error_msg)
                save_metadata(work_dir, metadata)
        else:
            metadata['phases_failed'].append(phase_name)
            metadata['errors'].append(error_msg)
            save_metadata(work_dir, metadata)
        print(f"\n⏱️  {error_msg}")
        return False

    except FileNotFoundError:
        error_msg = f"Phase script not found: {phase_script}"
        if metadata_lock:
            with metadata_lock:
                metadata['phases_failed'].append(phase_name)
                metadata['errors'].append(error_msg)
                save_metadata(work_dir, metadata)
        else:
            metadata['phases_failed'].append(phase_name)
            metadata['errors'].append(error_msg)
            save_metadata(work_dir, metadata)
        print(f"\n❌ {error_msg}")
        return False

    except Exception as e:
        error_msg = f"Phase '{phase_name}' encountered unexpected error: {str(e)}"
        if metadata_lock:
            with metadata_lock:
                metadata['phases_failed'].append(phase_name)
                metadata['errors'].append(error_msg)
                save_metadata(work_dir, metadata)
        else:
            metadata['phases_failed'].append(phase_name)
            metadata['errors'].append(error_msg)
            save_metadata(work_dir, metadata)
        print(f"\n❌ {error_msg}")
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Comprehensive stock research orchestrator'
    )
    parser.add_argument(
        'symbol',
        help='Stock ticker symbol (e.g., INTC, AAPL, MSFT)'
    )
    parser.add_argument(
        '--phases',
        default='all',
        help='Comma-separated list of phases to run (default: all)\n'
             'Available phases: technical, fundamental, research, sec, wikipedia, report'
    )
    parser.add_argument(
        '--skip-cleanup',
        action='store_true',
        help='Do not delete old work directories for this symbol'
    )
    parser.add_argument(
        '--peers',
        default=None,
        help='Comma-separated list of custom peer tickers (e.g., "GM,F,TM,RIVN")'
    )
    parser.add_argument(
        '--no-filter-peers',
        action='store_true',
        help='Disable automatic peer filtering (filtering is enabled by default)'
    )

    args = parser.parse_args()

    # Normalize symbol to uppercase
    symbol = args.symbol.upper()

    print("=" * 60)
    print("Stock Research Orchestrator")
    print("=" * 60)
    print(f"Symbol: {symbol}")
    print(f"Phases: {args.phases}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: Validate ticker
    print(f"\n{'='*60}")
    print("Step 1: Ticker Validation")
    print(f"{'='*60}")

    if not validate_ticker(symbol):
        print(f"\n❌ ERROR: Invalid ticker symbol '{symbol}'")
        print("Please check the ticker and try again.")
        return 1

    print(f"✓ Ticker '{symbol}' validated")

    # Step 2: Work Directory Setup
    print(f"\n{'='*60}")
    print("Step 2: Work Directory Setup")
    print(f"{'='*60}")

    # Determine work directory path
    date_str = datetime.now().strftime('%Y%m%d')
    work_dir = os.path.join(WORK_DIR, f"{symbol}_{date_str}")

    # Step 3: Cleanup old directories BEFORE creating new one
    cleanup_old_directories(symbol, work_dir, args.skip_cleanup)

    # Create new work directory
    os.makedirs(work_dir, exist_ok=True)
    print(f"✓ Created work directory: {work_dir}")

    # Step 4: Create metadata
    metadata = create_metadata(work_dir, symbol)

    # Step 5: Determine which phases to run
    all_phases = {
        'technical': 'skills/research_technical.py',
        'fundamental': 'skills/research_fundamental.py',
        'research': 'skills/research_perplexity.py',
        'analysis': 'skills/research_analysis.py',
        'sec': 'skills/research_sec.py',
        'wikipedia': 'skills/research_wikipedia.py',
        'report': 'skills/research_report.py',
        'deep': 'skills/research_deep.py',
        'final': 'skills/research_final.py'
    }

    if args.phases.lower() == 'all':
        phases_to_run = list(all_phases.keys())
    else:
        phases_to_run = [p.strip() for p in args.phases.split(',')]

    # Validate phase names
    invalid_phases = [p for p in phases_to_run if p not in all_phases]
    if invalid_phases:
        print(f"\n❌ ERROR: Invalid phase names: {', '.join(invalid_phases)}")
        print(f"Available phases: {', '.join(all_phases.keys())}")
        return 1

    # Validate API keys for phases to run
    print(f"\n{'='*60}")
    print("Step 3: API Key Validation")
    print(f"{'='*60}")

    valid_keys, missing_keys = validate_api_keys(phases_to_run)
    if not valid_keys:
        print(f"\n❌ ERROR: Required API keys are missing:")
        for key in missing_keys:
            print(f"  - {key}")
        print(f"\nPlease add the missing keys to your .env file and try again.")
        print(f"Example .env entry:")
        for key in missing_keys:
            print(f"  {key}=your_key_here")
        return 1

    print(f"✓ All required API keys are present")

    print(f"\n{'='*60}")
    print("Step 4: Get Company Overview")
    print(f"{'='*60}")
    print(f"Fetching foundational company data for {symbol}...")

    # Run company overview first (quick, foundational data)
    if save_company_overview(symbol, work_dir):
        print(f"✓ Company overview data ready")
    else:
        print(f"⚠ Warning: Could not fetch company overview, continuing with other phases...")

    print(f"\n{'='*60}")
    print("Step 5: Execute Research Phases")
    print(f"{'='*60}")
    print(f"Phases to run: {', '.join(phases_to_run)}")

    # Execute phases with dependencies
    success_count = 0
    failed_count = 0

    # Separate phases into groups for sequential execution
    # IMPORTANT: Technical phase MUST run first (generates peers list needed by fundamental)
    technical_phase = 'technical' in phases_to_run
    other_data_phases = [p for p in phases_to_run if p not in ['technical', 'report', 'deep', 'final']]
    report_phase = 'report' in phases_to_run
    deep_phase = 'deep' in phases_to_run
    final_phase = 'final' in phases_to_run

    # Execute technical phase FIRST (sequential) - generates peers list
    if technical_phase:
        print(f"\n{'='*60}")
        print("Executing technical phase (sequential - generates peer list)...")
        print(f"{'='*60}")

        phase_script = all_phases['technical']
        if os.path.exists(phase_script):
            # Add --peers and --no-filter-peers arguments for technical phase if specified
            extra_args = []
            if args.peers:
                extra_args.extend(['--peers', args.peers])
            if args.no_filter_peers:
                extra_args.append('--no-filter-peers')

            success = run_phase('technical', phase_script, symbol, work_dir, metadata, metadata_lock=None, extra_args=extra_args)
            if success:
                success_count += 1
            else:
                failed_count += 1
                print(f"\n⚠️  Warning: Technical phase failed - fundamental phase may have incomplete peer data")
        else:
            print(f"\n⊘ Skipping 'technical' - script not yet implemented")

    # Execute remaining data phases in parallel (if any)
    if other_data_phases:
        print(f"\n{'='*60}")
        print(f"Executing {len(other_data_phases)} remaining data phases in parallel...")
        print(f"(Technical phase already completed - peer list available)")
        print(f"{'='*60}")

        # Create a multiprocessing-compatible lock
        manager = Manager()
        metadata_lock = manager.Lock()

        with ProcessPoolExecutor(max_workers=6) as executor:
            # Submit all remaining data phase tasks
            future_to_phase = {}
            for phase_name in other_data_phases:
                phase_script = all_phases[phase_name]

                # Check if phase script exists
                if not os.path.exists(phase_script):
                    print(f"\n⊘ Skipping '{phase_name}' - script not yet implemented")
                    continue

                # No extra args for other phases
                future = executor.submit(run_phase, phase_name, phase_script, symbol, work_dir, metadata, metadata_lock, [])
                future_to_phase[future] = phase_name

            # Collect results as they complete
            for future in as_completed(future_to_phase):
                phase_name = future_to_phase[future]
                try:
                    success = future.result()
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"\n❌ Unexpected error in parallel execution for '{phase_name}': {e}")
                    failed_count += 1

    # Execute report phase sequentially (after all data gathered)
    if report_phase:
        phase_script = all_phases['report']
        if os.path.exists(phase_script):
            print(f"\n{'='*60}")
            print("Generating initial research report...")
            print(f"{'='*60}")
            success = run_phase('report', phase_script, symbol, work_dir, metadata)
            if success:
                success_count += 1
            else:
                failed_count += 1
        else:
            print(f"\n⊘ Skipping 'report' - script not yet implemented")

    # Execute deep research phase sequentially (after report)
    if deep_phase:
        phase_script = all_phases['deep']
        if os.path.exists(phase_script):
            print(f"\n{'='*60}")
            print("Running deep research with Claude API...")
            print("This may take a few minutes with extended thinking enabled...")
            print(f"{'='*60}")
            success = run_phase('deep', phase_script, symbol, work_dir, metadata)
            if success:
                success_count += 1
            else:
                failed_count += 1
        else:
            print(f"\n⊘ Skipping 'deep' - script not yet implemented")

    # Execute final report phase sequentially (after deep)
    if final_phase:
        phase_script = all_phases['final']
        if os.path.exists(phase_script):
            print(f"\n{'='*60}")
            print("Assembling final report with multi-format conversion...")
            print(f"{'='*60}")
            success = run_phase('final', phase_script, symbol, work_dir, metadata)
            if success:
                success_count += 1
            else:
                failed_count += 1
        else:
            print(f"\n⊘ Skipping 'final' - script not yet implemented")

    # Step 6: Final summary
    print(f"\n{'='*60}")
    print("Research Complete")
    print(f"{'='*60}")
    print(f"Symbol: {symbol}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Work directory: {work_dir}")
    print(f"Phases completed: {success_count}")
    print(f"Phases failed: {failed_count}")

    if metadata['phases_completed']:
        print(f"\n✓ Completed phases: {', '.join(metadata['phases_completed'])}")

    if metadata['phases_failed']:
        print(f"\n❌ Failed phases: {', '.join(metadata['phases_failed'])}")
        for error in metadata['errors']:
            print(f"  - {error}")

    print(f"\n{'='*60}")

    # Return success if at least one phase completed
    if success_count > 0:
        print("✓ Research partially or fully completed")
        print(f"✓ See outputs in: {work_dir}")
        return 0
    else:
        print("❌ No phases completed successfully")
        return 1


if __name__ == '__main__':
    sys.exit(main())
