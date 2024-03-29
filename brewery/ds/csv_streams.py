import csv
import codecs
import cStringIO
import base

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f, 'ignore')

    def __iter__(self):
        return self

    def next(self):
        line = self.reader.readline()
        if not line or line == '\0':
            raise StopIteration
        result = line.encode("utf-8")
        return result


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.

    From: <http://docs.python.org/lib/csv-examples.html>
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        new_row = []
        for value in row:
            if type(value) == unicode or type(value) == str:
                new_row.append(value.encode("utf-8"))
            else:
                new_row.append(unicode(value))

        self.writer.writerow(new_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class CSVDataSource(base.DataSource):
    """docstring for ClassName

    Some code taken from OKFN Swiss library.
    """
    def __init__(self, resource, read_header = True, dialect = None, encoding=None, detect_encoding = False,
                detect_header = False, sample_size = 200, **reader_args):
        """Creates a CSV data source stream.

        :Attributes:
            * resource: file name, URL or a file handle with CVS data
            * read_header: flag determining whether first line contains header or not.
                ``True`` by default.
            * encoding: source character encoding, by default no conversion is performed.
            * detect_encoding: read sample from source and determine whether source is UTF8 or not
            * detect_headers: try to determine whether data source has headers in first row or not
            * sample_size: maximum bytes to be read when detecting encoding and headers in file. By
                default it is set to 200 bytes to prevent loading huge CSV files at once.

        Note: avoid auto-detection when you are reading from remote URL stream.

        """
        self.read_header = read_header
        self.encoding = encoding
        self.detect_encoding = detect_encoding
        self.detect_header = detect_header

        self._autodetection = detect_encoding or detect_header

        self.sample_size = sample_size
        self.resource = resource
        self.reader_args = reader_args
        self.reader = None
        self.dialect = dialect

        self.close_file = False

        self._fields = None

    def initialize(self):
        """Initialize CSV source stream:

        #. perform autodetection if required:
            #. detect encoding from a sample data (if requested)
            #. detect whether CSV has headers from a sample data (if requested)
        #.  create CSV reader object
        #.   read CSV headers if requested and initialize stream fields

        """

        self.file, self.close_file = base.open_resource(self.resource)

        handle = None

        if self._autodetection:

            sample = self.file.read(self.sample_size)

            # Encoding test
            if self.detect_encoding:
                if type(sample) == unicode:
                    handle = UTF8Recoder(self.file, None)
                else:
                    sample = sample.decode(self.encoding)
                    handle = UTF8Recoder(self.file, self.encoding)

            if self.detect_header:
                sample = sample.encode('utf-8')
                sniffer = csv.Sniffer()
                self.read_header = sniffer.has_header(sample)

            self.file.seek(0)


        if not handle:
            handle = UTF8Recoder(self.file, self.encoding)

        if self.dialect:
            if type(self.dialect) == str:
                dialect = csv.get_dialect(self.dialect)
            else:
                dialect = self.dialect

            self.reader_args["dialect"] = dialect

        self.reader = csv.reader(handle, **self.reader_args)

        # Initialize field list
        if self.read_header:
            fields = self.reader.next()
            self._fields = base.fieldlist(fields)

    def finalize(self):
        if self.file and self.close_file:
            self.file.close()

    def rows(self):
        if not self.reader:
            raise RuntimeError("Stream is not initialized")
        return self.reader

    def get_fields(self):
        if not self._fields:
            raise ValueError("Fields are not initialized in CSV source")
        return self._fields

    def set_fields(self, fields):
        self._fields = fields

    fields = property(get_fields, set_fields)


class CSVDataTarget(base.DataTarget):
    def __init__(self, resource, write_headers = True, truncate = True, encoding = "utf-8",
                dialect = None, **kwds):
        """Creates a CSV data target

        :Attributes:
            * resource: target object - might be a filename or file-like object
            * write_headers: write field names as headers into output file
            * truncate: remove data from file before writing, default: True

        """
        self.resource = resource
        self.write_headers = write_headers
        self.truncate = truncate
        self._fields = None
        self.encoding = encoding
        self.dialect = dialect
        self.kwds = kwds

        self.close_file = False
        self.file = None
    def initialize(self):
        if self.truncate:
            mode = "w"
        else:
            mode = "a"

        self.file, self.close_file = base.open_resource(self.resource, mode)

        self.writer = UnicodeWriter(self.file, encoding = self.encoding,
                                    dialect = self.dialect, **self.kwds)

        if self.write_headers:
            self.writer.writerow(self.field_names)

    def finalize(self):
        if self.file and self.close_file:
            self.file.close()

    def get_fields(self):
        if not self._fields:
            raise ValueError("Fields are not initialized in CSV target")
        return self._fields

    def set_fields(self, fields):
        self._fields = fields

    fields = property(get_fields, set_fields)

    def append(self, obj):
        self.writer.writerow(obj)
