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

PipeName = 'Baseline QC'

########################################################################################################################
##########################################      ALGORITHM       ########################################################
########################################################################################################################

# Check baseline flatness using standard deviation in noise region
# Noise region: 10 to 11 ppm
# Baseline is PASS if std < 0.02

# Adjustable settings
BASELINE_SD_THRESHOLD = 0.02  # Maximum allowed standard deviation

########################################################################################################################
##########################################     GUI PIPE    #############################################################
########################################################################################################################


class BaselineGuiPipe(GuiPipe):
    preferredPipe = True
    pipeName = PipeName

    def __init__(self, name=pipeName, parent=None, project=None, **kwds):
        super(BaselineGuiPipe, self).__init__(parent=parent, name=name, project=project, **kwds)
        self._parent = parent


########################################################################################################################
##########################################       PIPE      #############################################################
########################################################################################################################


class BaselinePipe(SpectraPipe):
    guiPipe = BaselineGuiPipe
    pipeName = PipeName
    pipeCategory = PIPE_USER

    _kwargs = {}

    def runPipe(self, spectra, **kwargs):
        """
        Check baseline flatness.
        This method accepts and returns a list of Analysis Spectrum objects.
        """
        # Pipe variables
        pipeColumns = ['Baseline_SD_10to11ppm', 'Baseline_check']

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

            # Normalize intensities
            y_norm = y / np.max(y)

            # Extract noise region (10 to 11 ppm)
            noise_mask = (x >= 10) & (x <= 11)
            noise = y_norm[noise_mask]

            # Calculate baseline standard deviation
            baseline_sd = float('nan')
            baseline_check = 'CHECK'

            if len(noise) > 0:
                baseline_sd = float(np.std(noise))
                baseline_check = 'PASS' if baseline_sd < BASELINE_SD_THRESHOLD else 'CHECK'

            # Find matching row by spectrum name
            dfRows = qcDataTable.data.loc[qcDataTable.data['Spectrum'] == spectrumName]

            if len(dfRows) > 0:
                # Update existing row(s)
                for idx in dfRows.index:
                    qcDataTable.data.at[idx, 'Baseline_SD_10to11ppm'] = baseline_sd
                    qcDataTable.data.at[idx, 'Baseline_check'] = baseline_check
            else:
                # Create new row if spectrum not found
                new_row = {
                    'Spectrum': spectrumName,
                    'Baseline_SD_10to11ppm': baseline_sd,
                    'Baseline_check': baseline_check
                }
                qcDataTable.data = pd.concat([qcDataTable.data, pd.DataFrame([new_row])], ignore_index=True)

        return spectra


BaselinePipe.register()
