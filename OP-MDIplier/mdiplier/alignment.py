import subprocess
import os
import logging
import copy
import time
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import signal
#优化后的对齐算法
class Alignment:
    FILENAME_INPUT = "msa_input.fa"
    FILENAME_OUTPUT = "msa_output.txt"
    FILENAME_OUTPUT_ONELINE = "msa_output_oneline.txt"
    FILENAME_FIELDS_INFO = "msa_fields_info.txt"
    FILENAME_FIELDS_VISUAL = "msa_fields_visual.txt"
    
    # Enhanced timeout constants
    SMALL_PROTOCOL_TIMEOUT = 600      # 10 minutes
    MEDIUM_PROTOCOL_TIMEOUT = 3600    # 60 minutes
    LARGE_PROTOCOL_TIMEOUT = 7200     # 120 minutes
    EXTREME_PROTOCOL_TIMEOUT = 14400  # 240 minutes

    def __init__(self, messages, output_dir='tmp/', mode='ginsi', multithread=False, ep=0.123):
        self.messages = messages
        self.output_dir = output_dir
        self.mode = self._determine_mode(mode, len(messages))
        self.multithread = multithread
        self.ep = ep
        self.start_time = time.time()
        self.timeout = self._determine_timeout(len(messages))
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.filepath_input = os.path.join(self.output_dir, self.FILENAME_INPUT)
        self.filepath_output = os.path.join(self.output_dir, self.FILENAME_OUTPUT)
        self.filepath_output_oneline = os.path.join(self.output_dir, self.FILENAME_OUTPUT_ONELINE)
        self.filepath_fields_info = os.path.join(self.output_dir, self.FILENAME_FIELDS_INFO)
        self.filepath_fields_visual = os.path.join(self.output_dir, self.FILENAME_FIELDS_VISUAL)

        # Verify MAFFT installation during initialization
        self._verify_mafft_installation()

    def _verify_mafft_installation(self):
        """Verify MAFFT is properly installed and accessible"""
        try:
            # Try running a simple MAFFT command
            result = subprocess.run(
                ["mafft", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                raise RuntimeError(f"MAFFT verification failed: {error_msg}")
            
            logging.info(f"MAFFT version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError("MAFFT not found. Please install MAFFT and ensure it's in your PATH")

    def _determine_mode(self, requested_mode, message_count):
        if message_count > 3000:
            logging.info(f"Large dataset ({message_count} messages), using ginsi mode")
            return "ginsi"
        elif 500 <= message_count <= 1000:
            logging.info(f"Medium dataset ({message_count} messages), using linsi mode")
            return "linsi"
        return requested_mode

    def _determine_timeout(self, message_count):
        if message_count < 100:
            return self.SMALL_PROTOCOL_TIMEOUT
        elif 100 <= message_count < 500:
            return self.MEDIUM_PROTOCOL_TIMEOUT
        elif 500 <= message_count <= 1000:
            return self.LARGE_PROTOCOL_TIMEOUT
        else:
            return self.EXTREME_PROTOCOL_TIMEOUT

    def _log_phase(self, phase_name):
        elapsed = time.time() - self.start_time
        logging.info(f"\n{'='*40}\n[{phase_name.upper()}] (Elapsed: {elapsed:.1f}s)\n{'='*40}")

    def execute(self):
        try:
            logging.info(f"Starting alignment for {len(self.messages)} messages (timeout: {self.timeout//60} minutes)")
            
            self._log_phase("Input Preparation")
            self.create_mafft_input_with_tilde()
            
            # Log input file content for debugging
            self._log_input_file_content()
            
            self._log_phase("MAFFT Alignment")
            if not self._execute_mafft_with_timeout():
                raise TimeoutError(f"MAFFT alignment timed out after {self.timeout} seconds")
            
            self._log_phase("Output Processing")
            self.change_to_oneline()
            self.remove_character(self.filepath_output_oneline)
            
            self._log_phase("Field Analysis")
            self.generate_fields_info(self.filepath_output_oneline)
            self.generate_fields_visual_from_fieldsinfo()
            
            duration = time.time() - self.start_time
            logging.info(f"Alignment completed in {duration:.2f} seconds")
            return True
            
        except Exception as e:
            logging.error(f"Processing failed: {str(e)}")
            raise

    def _log_input_file_content(self):
        """Log first few lines of input file for debugging"""
        try:
            with open(self.filepath_input, 'r') as f:
                lines = [next(f) for _ in range(5)]
            logging.debug(f"Input file sample (first 5 lines):\n{''.join(lines)}")
        except Exception as e:
            logging.warning(f"Could not log input file content: {str(e)}")

    def _execute_mafft_with_timeout(self):
        def handler(signum, frame):
            raise TimeoutError("MAFFT execution timed out")
        
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.timeout)
        
        try:
            return self._execute_mafft_optimized()
        finally:
            signal.alarm(0)

    def _execute_mafft_optimized(self):
        """Optimized MAFFT execution with better error handling"""
        logging.info(f"Running {self.mode} alignment (timeout: {self.timeout//60} minutes)")
        
        if not os.path.exists(self.filepath_input):
            raise FileNotFoundError(f"Input file missing: {self.filepath_input}")
        
        # Check if input file has content
        input_size = os.path.getsize(self.filepath_input)
        if input_size == 0:
            raise ValueError(f"Input file is empty: {self.filepath_input}")
        logging.info(f"Input file size: {input_size} bytes")
        
        cmd = self._build_mafft_command()
        logging.info(f"Executing MAFFT command: {cmd}")
        
        try:
            # Create output directory if not exists
            os.makedirs(os.path.dirname(self.filepath_output), exist_ok=True)
            
            with open(self.filepath_output, 'w') as fout:
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=fout,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    preexec_fn=os.setsid
                )
                
                monitor_thread = threading.Thread(
                    target=self._monitor_mafft_process,
                    args=(process,)
                )
                monitor_thread.daemon = True
                monitor_thread.start()
                
                retcode = process.wait()
                monitor_thread.join()
                
                if retcode != 0:
                    error_output = process.stderr.read()
                    logging.error(f"MAFFT error output:\n{error_output}")
                    
                    # Check for common error patterns
                    if "No such file or directory" in error_output:
                        raise RuntimeError(f"MAFFT executable not found: {error_output}")
                    elif "invalid option" in error_output:
                        raise RuntimeError(f"Invalid MAFFT options: {error_output}")
                    elif "out of memory" in error_output.lower():
                        raise RuntimeError("MAFFT failed due to insufficient memory")
                    else:
                        raise RuntimeError(f"MAFFT failed with code {retcode}. Error output:\n{error_output}")
                
                # Verify output was created
                if not os.path.exists(self.filepath_output):
                    raise RuntimeError(f"MAFFT failed to create output file: {self.filepath_output}")
                
                output_size = os.path.getsize(self.filepath_output)
                if output_size == 0:
                    raise RuntimeError(f"MAFFT produced empty output file: {self.filepath_output}")
                
                logging.info(f"MAFFT output file created successfully, size: {output_size} bytes")
                return True
                
        except subprocess.SubprocessError as e:
            logging.error(f"MAFFT subprocess error: {str(e)}")
            raise RuntimeError(f"MAFFT execution failed: {str(e)}")

    def _build_mafft_command(self):
        """Build optimized MAFFT command with corrected parameter format"""
        # MAFFT mode mapping
        mode_mapping = {
            'ginsi': '--globalpair',
            'linsi': '--localpair',
            'einsi': '--genafpair'
        }
        
        # Get base command with correct parameter format
        if self.mode in mode_mapping:
            base_cmd = f"mafft {mode_mapping[self.mode]}"
        else:
            base_cmd = "mafft --auto"  # fallback to auto mode
        
        # Size-specific optimization parameters
        message_count = len(self.messages)
        if message_count > 2000:
            base_cmd += " --quiet --retree 1 --maxiterate 0"
        elif 500 <= message_count <= 1000:
            base_cmd += " --quiet --retree 1 --maxiterate 2"
        elif message_count > 100:
            base_cmd += " --quiet --retree 2"
        
        # Add common parameters
        base_cmd += f" --inputorder --text --ep {self.ep}"
        
        # Multithreading configuration
        if self.multithread:
            threads = min(multiprocessing.cpu_count(), 8)
            base_cmd += f" --thread {threads}"
            logging.info(f"Using {threads} threads")
        
        full_cmd = f"{base_cmd} {self.filepath_input}"
        logging.info(f"Final MAFFT command: {full_cmd}")
        return full_cmd

    def _monitor_mafft_process(self, process):
        last_update = time.time()
        no_output_timeout = 300
        last_progress = 0
        
        while process.poll() is None:
            line = process.stderr.readline()
            if line.strip():
                logging.info(f"MAFFT progress: {line.strip()}")
                last_update = time.time()
                
                if "iterative refinement" in line:
                    no_output_timeout = 600
                elif "building guide tree" in line:
                    no_output_timeout = 450
                elif "aligning sequences" in line:
                    if "%" in line:
                        try:
                            current_progress = int(line.split("%")[0].split()[-1])
                            if current_progress > last_progress:
                                no_output_timeout = max(300, (100-current_progress)*6)
                                last_progress = current_progress
                        except ValueError:
                            pass
                
            elapsed_no_output = time.time() - last_update
            if elapsed_no_output > no_output_timeout:
                logging.warning(f"MAFFT no output for {elapsed_no_output/60:.1f} minutes")
                self._terminate_process(process)
                raise RuntimeError("MAFFT process may be hung")
            
            time.sleep(15)

    def _terminate_process(self, process):
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as e:
            logging.warning(f"Error terminating process: {str(e)}")

    def create_mafft_input_with_tilde(self):
        message_data_hex = []
        for message in self.messages:
            try:
                message_data_hex.append(message.data.hex())
            except AttributeError:
                logging.warning("Skipping message with invalid data")
                continue
        
        logging.info(f"Creating MAFFT input for {len(message_data_hex)} messages")
        
        with open(self.filepath_input, 'w') as f:
            for i, hex_str in enumerate(message_data_hex):
                formatted = '~'.join([hex_str[j:j+2] for j in range(0, len(hex_str), 2)])
                f.write(f">{i}\n{formatted}\n")

    def change_to_oneline(self):
        logging.info("Converting to one-line format")
        
        if not os.path.isfile(self.filepath_output):
            raise FileNotFoundError("MAFFT output file missing")
        
        try:
            with open(self.filepath_output, 'r') as fin, \
                 open(self.filepath_output_oneline, 'w') as fout:
                
                isfirstline = True
                for line in fin:
                    if line.startswith('>'):
                        if isfirstline:
                            isfirstline = False
                        else:
                            fout.write("\n")
                    else:
                        fout.write(line.strip())
        except Exception as e:
            raise RuntimeError(f"Failed to convert to oneline: {str(e)}")

    def remove_character(self, filepath):
        logging.info("Removing gap characters")
        
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        try:
            with open(filepath) as f:
                linelist = f.read().splitlines()

            keep_cols = []
            for col in range(len(linelist[0])):
                keep = False
                for line in linelist:
                    if col < len(line) and line[col] not in ['-', '~']:
                        keep = True
                        break
                if keep:
                    keep_cols.append(col)
            
            with open(filepath, 'w') as fout:
                for line in linelist:
                    filtered = ''.join(line[col] for col in keep_cols if col < len(line))
                    fout.write(filtered + "\n")
                    
        except Exception as e:
            raise RuntimeError(f"Failed to remove characters: {str(e)}")

    def generate_fields_info(self, filepath_input):
        logging.info("Generating field info with types")
        
        if not os.path.isfile(filepath_input):
            raise FileNotFoundError(f"Input file missing: {filepath_input}")
        
        try:
            with open(filepath_input) as f:
                linelist = [line.strip() for line in f.readlines()]
                
            if not linelist:
                logging.warning("Empty aligned data file")
                return
                
            length_message = max(len(line) for line in linelist) if linelist else 0
            results_fields = []
            i = 0
            isLastStatic = False
            
            while i < length_message:
                offset = 2
                while i + offset <= length_message:
                    valuelist = [line[i:i+offset] if i < len(line) else "" for line in linelist]
                    if not self.has_even_number_of_bytes(valuelist):
                        offset += 1
                        continue
                    else:
                        break
                
                if not all(len(val) == offset for val in valuelist):
                    valuelist = [val.ljust(offset) for val in valuelist]
                
                if not len(set(valuelist)) == 1:
                    if self.is_variable_field(valuelist):
                        field_type = 'V'
                    else:
                        field_type = 'D'
                    results_fields.append([offset, field_type])
                    isLastStatic = False
                else:
                    if isLastStatic:
                        results_fields[-1][0] += offset
                    else:
                        results_fields.append([offset, 'S'])
                    isLastStatic = True

                i += offset
            
            with open(self.filepath_fields_info, 'w') as fout:
                for size, ftype in results_fields:
                    fout.write(f"Raw 0 {size*8} {ftype}\n")
            
            logging.info(f"Generated {len(results_fields)} fields")
            
        except Exception as e:
            raise RuntimeError(f"Field analysis failed: {str(e)}")

    def has_even_number_of_bytes(self, valuelist):
        for value in valuelist:
            clean_value = value.replace("-", "").replace("~", "")
            if len(clean_value) % 2 != 0:
                return False
        return True

    def is_variable_field(self, valuelist):
        for value in valuelist:
            if '-' in value:
                return True
        return False

    def generate_fields_visual_from_fieldsinfo(self):
        logging.info("Generating field visualization")
        
        fields_info = self.get_fields_info()
        
        if not os.path.isfile(self.filepath_output_oneline):
            raise FileNotFoundError("Aligned data file missing")
        
        try:
            with open(self.filepath_output_oneline) as f:
                messages_data_mafft = [line.strip() for line in f.readlines()]
                
            with open(self.filepath_fields_visual, 'w') as fout:
                for msg_data in messages_data_mafft:
                    segments = []
                    pos_start = 0
                    for pos_end in sorted(fields_info.keys()):
                        if pos_end <= len(msg_data):
                            segments.append(msg_data[pos_start:pos_end])
                            pos_start = pos_end
                    if pos_start < len(msg_data):
                        segments.append(msg_data[pos_start:])
                    fout.write(' '.join(segments) + '\n')
                    
        except Exception as e:
            raise RuntimeError(f"Field visualization failed: {str(e)}")

    def get_fields_info(self):
        if not os.path.isfile(self.filepath_fields_info):
            raise FileNotFoundError("Field info file missing")
        
        fields_info = {}
        pos = 0
        with open(self.filepath_fields_info) as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4:
                    size_bits = int(parts[2])
                    pos += size_bits // 8
                    fields_info[pos] = parts[3]  # Field type (S/V/D)
        return fields_info

    @staticmethod
    def get_messages_aligned(messages, filepath_output_oneline):
        if not messages or not filepath_output_oneline:
            return []
        
        aligned_messages = copy.deepcopy(messages)
        
        try:
            with open(filepath_output_oneline, 'r') as f:
                for i, line in enumerate(f):
                    if i < len(aligned_messages):
                        aligned_messages[i].data = line.strip()
        except IOError as e:
            logging.error(f"Failed to load aligned messages: {str(e)}")
        
        return aligned_messages