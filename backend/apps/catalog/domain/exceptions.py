class CatalogBaseError(Exception):
    pass


class CatalogProductListEmptyError(CatalogBaseError):
    pass


class CatalogFavoriteItemExistError(CatalogBaseError):
    pass


class CatalogInvalidStockOperationError(CatalogBaseError):
    pass


class CatalogOutOfStockError(CatalogBaseError):
    pass


class CatalogStockInconsistencyError(CatalogBaseError):
    pass


class CatalogDigitalAssetAlreadyUsedError(CatalogBaseError):
    pass


class CatalogDigitalAssetConflictError(CatalogBaseError):
    pass


class CatalogDigitalAssetOutOfStockError(CatalogBaseError):
    pass


class CatalogProductNotPurchasedError(CatalogBaseError):
    pass


class CatalogReviewAlreadyExistsError(CatalogBaseError):
    pass
