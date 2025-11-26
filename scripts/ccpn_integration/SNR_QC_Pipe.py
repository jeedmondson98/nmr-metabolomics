#### GUI IMPORTS
from ccpn.ui.gui.widgets.PipelineWidgets import GuiPipe

#### NON GUI IMPORTS
from ccpn.framework.lib.pipeline.PipeBase import SpectraPipe, PIPE_USER
from ccpn.util.Logging import getLogger
import numpy as np
import pandas as pd

########################################################################################################################
###   Attributes:
########################################################################################################################

PipeName = 'SNR QC'

########################################################################################################################
##########################################      ALGORITHM       ########################################################
########################################################################################################################

# Calculate Signal-to-Noise Ratio
# Signal region: 0.5 to 4 ppm
# Noise region: 10 to 11 ppm
# SNR = signal_max / noise_std

# Adjustable settings
SNR_THRESHOLD = 10  # Minimum acceptable SNR

########################################################################################################################
##########################################     GUI PIPE    #############################################################
########################################################################################################################


class SNRGuiPipe(GuiPipe):
    preferredPipe = True
    pipeName = PipeName

    def __init__(self, name=pipeName, parent=None, project=None, **kwds):
        super(SNRGuiPipe, self).__init__(parent=parent, name=name, project=project, **kwds)
        self._parent = parent


########################################################################################################################
##########################################       PIPE      #############################################################
########################################################################################################################


class SNRPipe(SpectraPipe):
    guiPipe = SNRGuiPipe
    pipeName = PipeName
    pipeCategory = PIPE_USER

    _kwargs = {}

    def runPipe(self, spectra, **kwargs):
        """
        Calculate Signal-to-Noise Ratio.
        This method accepts and returns a list of Analysis Spectrum objects.
        """
        # Pipe variables
        pipeColumns = ['SNR', 'SNR_check']

        # Establish dataTable
        qcDataTable = self.project.getByPid('DT:QC_Results')
        if not qcDataTable:
            columns = ['Spectrum'] + pipeColumns
            qcDataTable = self.project.newDataTable(name='QC_Results', data=pd.DataFrame(columns=columns))
        else:
            # Only add columns if they don't already exist
            for col in pipeColumns:
                if col not in qcDataTable.data.columns:
                    qcDataTable.data[col] = None

        for spectrum in spectra:
            spectrumName = spectrum.name
            x = spectrum.positions
            y = spectrum.intensities

            # Normalize intensities to 0-1
            y_norm = y / np.max(y)

            # Extract signal region (0.5 to 4 ppm)
            signal_mask = (x >= 0.5) & (x <= 4)
            signal = y_norm[signal_mask]

            # Extract noise region (10 to 11 ppm)
            noise_mask = (x >= 10) & (x <= 11)
            noise = y_norm[noise_mask]

            # Calculate SNR - ensure proper types
            snr = float('nan')
            if len(noise) > 0 and len(signal) > 0:
                noise_std = float(np.std(noise))
                if noise_std > 0:
                    snr = float(np.max(signal)) / noise_std

            # Pass/fail based on SNR threshold
            if np.isnan(snr):
                snr_check = 'CHECK'
            else:
                snr_check = 'PASS' if snr > SNR_THRESHOLD else 'CHECK'

            # Find matching row by spectrum name
            dfRows = qcDataTable.data.loc[qcDataTable.data['Spectrum'] == spectrumName]

            if len(dfRows) > 0:
                # Update existing row(s)
                for idx in dfRows.index:
                    qcDataTable.data.at[idx, 'SNR'] = snr
                    qcDataTable.data.at[idx, 'SNR_check'] = snr_check
            else:
                # Create new row if spectrum not found
                new_row = {'Spectrum': spectrumName, 'SNR': snr, 'SNR_check': snr_check}
                qcDataTable.data = pd.concat([qcDataTable.data, pd.DataFrame([new_row])], ignore_index=True)

        return spectra


SNRPipe.register()
