#### GUI IMPORTS
from ccpn.ui.gui.widgets.PipelineWidgets import GuiPipe

#### NON GUI IMPORTS
from ccpn.framework.lib.pipeline.PipeBase import SpectraPipe, PIPE_USER
from ccpn.util.Logging import getLogger
import numpy as np
import pandas as pd

logger = getLogger()

########################################################################################################################
###   Attributes:
########################################################################################################################

PipeName = 'QC Summary Report'

########################################################################################################################
##########################################      ALGORITHM       ########################################################
########################################################################################################################

# Generate a summary report of all QC results
# Adds summary columns to data table showing:
# - Overall QC status (PASS/CHECK)
# - Number of issues found
# - Which checks need attention

########################################################################################################################
##########################################     GUI PIPE    #############################################################
########################################################################################################################


class SummaryGuiPipe(GuiPipe):
    preferredPipe = True
    pipeName = PipeName

    def __init__(self, name=pipeName, parent=None, project=None, **kwds):
        super(SummaryGuiPipe, self).__init__(parent=parent, name=name, project=project, **kwds)
        self._parent = parent


########################################################################################################################
##########################################       PIPE      #############################################################
########################################################################################################################


class SummaryPipe(SpectraPipe):
    guiPipe = SummaryGuiPipe
    pipeName = PipeName
    pipeCategory = PIPE_USER

    _kwargs = {}

    def runPipe(self, spectra, **kwargs):
        """
        Generate a summary report and add columns to QC data table.
        Adds: Overall_QC, Issues_Found, Failed_Checks
        """
        # Get the QC data table
        qcDataTable = self.project.getByPid('DT:QC_Results')
        if not qcDataTable:
            logger.info("No QC_Results table found. Run other QC pipes first.")
            return spectra
        
        df = qcDataTable.data
        
        if len(df) == 0:
            logger.info("QC_Results table is empty.")
            return spectra
        
        # Add summary columns if they don't exist
        summary_columns = ['Overall_QC', 'Issues_Found', 'Failed_Checks']
        for col in summary_columns:
            if col not in df.columns:
                df[col] = None
        
        # Define which columns contain pass/fail info (all end with _check now)
        check_cols = [col for col in df.columns if col.endswith('_check')]
        
        # Calculate summary for each row
        for idx, row in df.iterrows():
            failed_checks = []
            issues_count = 0
            
            # Find which checks failed
            for col in check_cols:
                if col in row.index:
                    value = row[col]
                    if value == 'CHECK':
                        # Get the name without _check suffix
                        check_name = col.replace('_check', '')
                        failed_checks.append(check_name)
                        issues_count += 1
            
            # Determine overall QC status
            if issues_count == 0:
                overall_qc = 'PASS'
            else:
                overall_qc = 'CHECK'
            
            # Create failed checks string
            failed_str = ', '.join(failed_checks) if failed_checks else 'None'
            
            # Update the row
            qcDataTable.data.at[idx, 'Overall_QC'] = overall_qc
            qcDataTable.data.at[idx, 'Issues_Found'] = issues_count
            qcDataTable.data.at[idx, 'Failed_Checks'] = failed_str
        
        # ===== PRINT SUMMARY REPORT TO CONSOLE =====
        logger.info("\n" + "="*80)
        logger.info("QC SUMMARY REPORT")
        logger.info("="*80)
        
        total_spectra = len(df)
        logger.info(f"\nTotal spectra: {total_spectra}")
        
        # ===== SNR CHECK =====
        if 'SNR_check' in df.columns:
            snr_pass = (df['SNR_check'] == 'PASS').sum()
            snr_fail = total_spectra - snr_pass
            snr_pct = (snr_pass / total_spectra * 100) if total_spectra > 0 else 0
            logger.info(f"\nSNR Check:")
            logger.info(f"  PASS: {snr_pass}/{total_spectra} ({snr_pct:.1f}%)")
            logger.info(f"  CHECK: {snr_fail}/{total_spectra}")
        
        # ===== TSP CHECK =====
        if 'TSP_check' in df.columns:
            tsp_pass = (df['TSP_check'] == 'PASS').sum()
            tsp_fail = total_spectra - tsp_pass
            tsp_pct = (tsp_pass / total_spectra * 100) if total_spectra > 0 else 0
            logger.info(f"\nTSP Symmetry Check:")
            logger.info(f"  PASS: {tsp_pass}/{total_spectra} ({tsp_pct:.1f}%)")
            logger.info(f"  CHECK: {tsp_fail}/{total_spectra}")
        
        # ===== BASELINE CHECK =====
        if 'Baseline_check' in df.columns:
            baseline_pass = (df['Baseline_check'] == 'PASS').sum()
            baseline_fail = total_spectra - baseline_pass
            baseline_pct = (baseline_pass / total_spectra * 100) if total_spectra > 0 else 0
            logger.info(f"\nBaseline Flatness Check:")
            logger.info(f"  PASS: {baseline_pass}/{total_spectra} ({baseline_pct:.1f}%)")
            logger.info(f"  CHECK: {baseline_fail}/{total_spectra}")
        
        # ===== WATER SUPPRESSION CHECK =====
        if 'Water_check' in df.columns:
            water_pass = (df['Water_check'] == 'PASS').sum()
            water_fail = total_spectra - water_pass
            water_pct = (water_pass / total_spectra * 100) if total_spectra > 0 else 0
            logger.info(f"\nWater Suppression Check:")
            logger.info(f"  PASS: {water_pass}/{total_spectra} ({water_pct:.1f}%)")
            logger.info(f"  CHECK: {water_fail}/{total_spectra}")
        
        # ===== OVERALL QC STATUS =====
        overall_pass = (df['Overall_QC'] == 'PASS').sum()
        overall_fail = total_spectra - overall_pass
        overall_pct = (overall_pass / total_spectra * 100) if total_spectra > 0 else 0
        logger.info(f"\nOVERALL QC STATUS:")
        logger.info(f"  PASS: {overall_pass}/{total_spectra} ({overall_pct:.1f}%)")
        logger.info(f"  CHECK: {overall_fail}/{total_spectra}")
        
        # ===== SPECTRA NEEDING ATTENTION =====
        logger.info(f"\n{'-'*80}")
        logger.info("SPECTRA NEEDING ATTENTION:")
        logger.info(f"{'-'*80}")
        
        needs_attention = df[df['Issues_Found'] > 0]
        
        if len(needs_attention) > 0:
            for idx, row in needs_attention.iterrows():
                spectrum_name = row['Spectrum']
                issues = row['Issues_Found']
                failed = row['Failed_Checks']
                logger.info(f"\n  {spectrum_name}:")
                logger.info(f"    Issues: {issues}")
                logger.info(f"    Checks to review: {failed}")
        else:
            logger.info("  All spectra PASS!")
        
        # ===== OVERALL STATISTICS =====
        logger.info(f"\n{'-'*80}")
        logger.info("STATISTICS:")
        logger.info(f"{'-'*80}")
        
        if 'SNR' in df.columns:
            snr_valid = df['SNR'].replace([np.inf, -np.inf], np.nan).dropna()
            if len(snr_valid) > 0:
                snr_mean = snr_valid.mean()
                snr_min = snr_valid.min()
                snr_max = snr_valid.max()
                logger.info(f"\nSNR:")
                logger.info(f"  Mean: {snr_mean:.1f}")
                logger.info(f"  Min: {snr_min:.1f}")
                logger.info(f"  Max: {snr_max:.1f}")
        
        if 'Ref_linewidth_Hz' in df.columns:
            lw_valid = df['Ref_linewidth_Hz'].dropna()
            if len(lw_valid) > 0:
                lw_mean = lw_valid.mean()
                lw_min = lw_valid.min()
                lw_max = lw_valid.max()
                logger.info(f"\nTSP Linewidth (Hz):")
                logger.info(f"  Mean: {lw_mean:.2f}")
                logger.info(f"  Min: {lw_min:.2f}")
                logger.info(f"  Max: {lw_max:.2f}")
        
        if 'Baseline_SD_10to11ppm' in df.columns:
            baseline_valid = df['Baseline_SD_10to11ppm'].dropna()
            if len(baseline_valid) > 0:
                baseline_mean = baseline_valid.mean()
                baseline_min = baseline_valid.min()
                baseline_max = baseline_valid.max()
                logger.info(f"\nBaseline SD (10-11 ppm):")
                logger.info(f"  Mean: {baseline_mean:.6f}")
                logger.info(f"  Min: {baseline_min:.6f}")
                logger.info(f"  Max: {baseline_max:.6f}")
        
        if 'Water_elevation_ratio' in df.columns:
            water_valid = df['Water_elevation_ratio'].dropna()
            if len(water_valid) > 0:
                water_mean = water_valid.mean()
                water_min = water_valid.min()
                water_max = water_valid.max()
                logger.info(f"\nWater Elevation Ratio:")
                logger.info(f"  Mean: {water_mean:.3f}")
                logger.info(f"  Min: {water_min:.3f}")
                logger.info(f"  Max: {water_max:.3f}")
        
        logger.info(f"\n{'='*80}\n")
        
        return spectra


SummaryPipe.register()
