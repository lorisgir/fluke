import io as _io
import typing as _typ
from abc import ABC as _ABC
from abc import abstractmethod as _absmethod
from shutil import copyfileobj as _copyfileobj


from ._helper import infer_separator as _infer_sep
from ._handlers import SSHClientHandler as _SSHClientHandler
from ._handlers import AWSClientHandler as _AWSClientHandler
from ._handlers import AzureClientHandler as _AzureClientHandler


class Ingester(_ABC):
    '''
    An abstract class which serves as the \
    base class for all ingester-like classes.
    '''

    def __init__(self):
        '''
        An abstract class which serves as the \
        base class for all ingester-like classes.
        '''
        self.__src = None
        self.__snk = None
        self.__metadata = None

    def get_source(self) -> _typ.Optional[_typ.Any]:
        '''
        Returns the ingester's current source.
        '''
        return self.__src

    def set_source(self, src: _typ.Any):
        '''
        Sets the ingester's current source.

        :param Any src: The source that is to be set.
        '''
        self.__src = src

    def get_sink(self)-> _typ.Optional[_typ.Any]:
        '''
        Returns the ingester's current sink.
        '''
        return self.__snk

    def set_sink(self, snk: _typ.Any):
        '''
        Sets the ingester's current sink.

        :param Any snk: The sink that is to be set.
        '''
        self.__snk = snk

    def get_metadata(self) -> dict[str, str]:
        '''
        Returns any metadata currently held \
        by the ingester.
        '''
        return self.__metadata

    def set_metadata(self, metadata: dict[str, str]):
        '''
        Sets the metadata that is currently \
        held by the ingester.

        :param dict[str, str] metadata: A dictionary \
            containing the metadata.
        '''
        self.__metadata = metadata


    @_absmethod
    def extract(
        self,
        snk: _typ.Union[_io.BufferedReader, _io.BytesIO],
        include_metadata: bool
    ) -> None:
        '''
        Extracts data from the currently set source \
        and into the provided sink.

        :param Union[BufferedReader, BytesIO] snk: A \
            buffer acting as a sink.
        :param bool include_metadata: Indicates whether \
            to ingest any existing metadata along with \
            the primarily ingested data.
        '''
        pass


    @_absmethod
    def load(
        self,
        src: _typ.Union[_io.BufferedReader, _io.BytesIO],
        metadata: dict[str, str]
    ) -> None:
        '''
        Loads data from the provided source and \
        into the currently set sink.

        :param Union[BufferedReader, BytesIO] src: A \
            buffer acting as a source.
        :param dict[str, str]: A dictionary containing \
            metadata that are to be assigned to the \
            primarily ingested data.
        '''
        pass


class LocalIngester(Ingester):
    '''
    A class used in extracting data from a local source, \
    as well as loading data into a local sink.
    '''

    def __init__(self):
        '''
        A class used in extracting data from a local source, \
        as well as loading data into a local sink.
        '''
        super().__init__()


    def extract(
        self,
        snk: _typ.Union[_io.BufferedReader, _io.BytesIO],
        include_metadata: bool
    ) -> None:
        '''
        Extracts data from the currently set source \
        and into the provided sink.

        :param Union[BufferedReader, BytesIO] snk: A \
            buffer acting as a sink.
        :param bool include_metadata: Indicates whether \
            to ingest any existing metadata along with \
            the primarily ingested data.

        :note: Param ``include_metadata`` has no use within \
            the context of method ``LocalIngester.extract``.
        '''
        
        # NOTE: This method is not currently invoked,
        #       as local files are read directly into
        #       memory and are not written into a buffer.
        _copyfileobj(fsrc=self.get_source(), fdst=snk)


    def load(
        self,
        src: _typ.Union[_io.BufferedReader, _io.BytesIO],
        metadata: dict[str, str]
    ) -> None:
        '''
        Loads data from the provided source and \
        into the currently set sink.

        :param Union[BufferedReader, BytesIO] src: A \
            buffer acting as a source.
        :param dict[str, str]: A dictionary containing \
            metadata that are to be assigned to the \
            primarily ingested data.

        :note: Param ``metadata`` has no use within the \
            context of method ``LocalIngester.load``.
        '''
        _copyfileobj(fsrc=src, fdst=self.get_sink())


class RemoteIngester(Ingester):
    '''
    A class used in extracting data from a remote source, \
    as well as loading data into a remote sink.

    :param SSHClientHandler handler: An ``SSHClientHandler`` \
        instance through which access to a remote server is provided.
    '''


    def __init__(self, handler: _SSHClientHandler):
        '''
        A class used in extracting data from a remote source, \
        as well as loading data into a remote sink.

        :param SSHClientHandler handler: An ``SSHClientHandler`` \
            instance through which access to a remote server is provided.
        '''
        super().__init__()
        self.__handler = handler


    def extract(
        self,
        snk: _typ.Union[_io.BufferedReader, _io.BytesIO],
        include_metadata: bool
    ) -> None:
        '''
        Extracts data from the currently set source \
        and into the provided sink.

        :param Union[BufferedReader, BytesIO] snk: A \
            buffer acting as a sink.
        :param bool include_metadata: Indicates whether \
            to ingest any existing metadata along with \
            the primarily ingested data.

        :note: Param ``include_metadata`` has no use within \
            the context of method ``RemoteIngester.extract``.
        '''
        self.__handler.download_file(
            file_path=self.get_source(),
            buffer=snk,
            include_metadata=include_metadata)


    def load(
        self,
        src: _typ.Union[_io.BufferedReader, _io.BytesIO],
        metadata: dict[str, str]
    ) -> None:
        '''
        Loads data from the provided source and \
        into the currently set sink.

        :param Union[BufferedReader, BytesIO] src: A \
            buffer acting as a source.
        :param dict[str, str]: A dictionary containing \
            metadata that are to be assigned to the \
            primarily ingested data.

        :note: Param ``metadata`` has no use within the \
            context of method ``RemoteIngester.load``.
        '''

        file_path: str = self.get_sink()

        sep = _infer_sep(file_path)

        def get_parent_dir(file_path: str) -> _typ.Optional[str]:
            file_path = file_path.rstrip(sep)
            if sep in file_path:
                return f"{sep.join(file_path.split(sep)[:-1])}{sep}"
            return None

        # Create any directories necessary.
        parent_dir, non_existing_dirs = file_path, []
        while (parent_dir := get_parent_dir(parent_dir)) is not None:
            if not self.__handler.path_exists(path=parent_dir):
                non_existing_dirs.append(parent_dir)

        for dir in reversed(non_existing_dirs):
            self.__handler.mkdir(path=dir)

        # Load file to remote location.
        self.__handler.upload_file(
            file_path=file_path,
            buffer=src,
            metadata=metadata)


class AWSS3Ingester(Ingester):
    '''
    A class used in extracting data from an Amazon S3 bucket, \
    as well as loading data into an Amazon S3 bucket.

    :param AWSClientHandler handler: An ``AWSClientHandler`` \
        instance through which access to an Amazon S3 bucket is \
        provided.
    '''

    def __init__(self, handler: _AWSClientHandler):
        '''
        A class used in extracting data from an Amazon S3 bucket, \
        as well as loading data into an Amazon S3 bucket.

        :param AWSClientHandler handler: An ``AWSClientHandler`` \
            instance through which access to an Amazon S3 bucket is \
            provided.
        '''
        self.__handler = handler
        super().__init__()

    
    def extract(
        self,
        snk: _typ.Union[_io.BufferedReader, _io.BytesIO],
        include_metadata: bool
    ) -> None:
        '''
        Extracts data from the currently set source \
        and into the provided sink.

        :param Union[BufferedReader, BytesIO] snk: A \
            buffer acting as a sink.
        :param bool include_metadata: Indicates whether \
            to ingest any existing metadata along with \
            the primarily ingested data.
        '''
        if (metadata := self.__handler.download_file(
            file_path=self.get_source(),
            buffer=snk,
            include_metadata=include_metadata)
        ) is not None:
            self.set_metadata(metadata)


    def load(
        self,
        src: _typ.Union[_io.BufferedReader, _io.BytesIO],
        metadata: dict[str, str]
    ) -> None:
        '''
        Loads data from the provided source and \
        into the currently set sink.

        :param Union[BufferedReader, BytesIO] src: A \
            buffer acting as a source.
        :param dict[str, str]: A dictionary containing \
            metadata that are to be assigned to the \
            primarily ingested data.
        '''
        self.__handler.upload_file(
            file_path=self.get_sink(),
            buffer=src,
            metadata=metadata)


class AzureIngester(Ingester):
    '''
    A class used in extracting data from an Azure blob container, \
    as well as loading data into an Azure blob container.

    :param AzureClientHandler handler: An ``AzureClientHandler`` \
        instance through which access to an Azure blob container \
        is provided.
    '''

    def __init__(
        self,
        handler: _AzureClientHandler
    ):
        '''
        A class used in extracting data from an Azure blob container, \
        as well as loading data into an Azure blob container.

        :param AzureClientHandler handler: An ``AzureClientHandler`` \
            instance through which access to an Azure blob container \
            is provided.
        '''
        self.__handler = handler
        super().__init__()

    
    def extract(
        self,
        snk: _typ.Union[_io.BufferedReader, _io.BytesIO],
        include_metadata: bool
    ) -> None:
        '''
        Extracts data from the currently set source \
        and into the provided sink.

        :param Union[BufferedReader, BytesIO] snk: A \
            buffer acting as a sink.
        :param bool include_metadata: Indicates whether \
            to ingest any existing metadata along with \
            the primarily ingested data.
        '''
        if (metadata := self.__handler.download_file(
            file_path=self.get_source(),
            buffer=snk,
            include_metadata=include_metadata)
        ) is not None:
            self.set_metadata(metadata)


    def load(
        self,
        src: _typ.Union[_io.BufferedReader, _io.BytesIO],
        metadata: dict[str, str]
    ) -> None:
        '''
        Loads data from the provided source and \
        into the currently set sink.

        :param Union[BufferedReader, BytesIO] src: A \
            buffer acting as a source.
        :param dict[str, str]: A dictionary containing \
            metadata that are to be assigned to the \
            primarily ingested data.
        '''
        self.__handler.upload_file(
            file_path=self.get_sink(),
            buffer=src,
            metadata=metadata)
    